from __future__ import annotations
from pygame import *
from collections.abc import Callable
from typing import Literal
import random as r
import time as t
import socket
import select
import math

type Card = Mob|Item
type Coord = tuple[int|float,int|float]
type Size = tuple[int,int]
type Path = str
type Attack_params = dict[Literal["origin"]:Card,Literal["target"]:Card,Literal["damage"]:int,Literal["noattack"]:bool]
#Name:LAPTOP-20C14P7N, Address:172.20.57.66
#None values mean add later

class Mob(sprite.Sprite):
    def __init__(self,name:str,cost:int,health:int,abilities:list[Callable],attacks:list[Callable],passives:dict[Literal["end of turn","start of turn","on death","on hurt","on attack","when played"],Callable],items:dict[Literal["end of turn","start of turn","on death","on hurt","on attack","when played"],Item],mob_class:Literal["undead","arthropod","aquatic","human","misc"],biome:Literal["plains","cavern","ocean","swamp"],border:Literal["blue","pink"],sprite:Path,init_pos:Coord,cut_sprite:Path,move_positions:list[tuple[int,int,int,int]]):
        super().__init__()
        #MOB INFO
        self.name=name
        self.cost=cost
        self.health=health
        self.max_health=health
        #passives listed first on card, then attacks, then abilities
        self.abilities=abilities 
        self.passives=passives #dict, index is a trigger marker which allows functions to know when to call it, same for items
        self.moveset=attacks + abilities #used for finding which one was clicked
        self.move_positions=[]
        for position in move_positions:
            self.move_positions.append(Rect(position[0],position[1],position[2]-position[0],position[3]-position[1]))#hitboxes of moves, in order
        self.items=items
        self.mob_class=mob_class
        self.biome=biome
        self.status={"psn":0,"frz":0,"fire":0}
        self.border=border #blue or pink
        #SPRITE AND COORDS
        self.front_sprite=transform.scale(image.load(sprite),card_dim)
        self.original_sprite=sprite
        self.cut_sprite=transform.scale(image.load(cut_sprite),cut_dim)
        self.back_sprite=transform.scale(image.load(cardback),card_dim)
        self.current_sprite=self.front_sprite
        self.rect=self.current_sprite.get_rect()
        self.rect.x=init_pos[0]
        self.rect.y=init_pos[1]
        #MOVEMENT
        self.movement_phase=0 #indicates which location is currently being moved to
        self.destinations=[] #the list of locations to move to, in order
        self.times=[]
        self.timer=0
        self.velocity=(0,0)

    def startmove(self,dests:list[Coord],times:list[int]):
        if self.timer==0:
            self.destinations=dests
            self.times=times
            self.timer=self.times[self.movement_phase]
            self.velocity=((self.destinations[self.movement_phase][0]-self.rect.x)/self.timer, (self.destinations[self.movement_phase][1]-self.rect.y)/self.timer)

    def update(self):
        global move_hovering_over
        if self.timer!=0:
            self.rect.x+=self.velocity[0]
            self.rect.y+=self.velocity[1]
            self.timer-=1
        elif self.timer == 0 and self.movement_phase != len(self.destinations)-1 and self.destinations != []:
            self.movement_phase += 1
            self.timer=self.times[self.movement_phase]
            self.velocity=((self.destinations[self.movement_phase][0]-self.rect.x)/self.timer, (self.destinations[self.movement_phase][1]-self.rect.y)/self.timer)
        else:
            self.destinations=[]
            self.times=[]
            self.movement_phase=0
        for position in self.move_positions:
            if selected == self and position.collidepoint(mouse.get_pos()) and not attack_progressing and self == player1.field[subturn-1]:
                draw.rect(screen,ORANGE,position,5)
                move_hovering_over=(position,self.moveset[self.move_positions.index(position)])
        if attack_progressing:
            draw.rect(screen,ORANGE,move_hovering_over[0],5)
        for item in self.items:
            if len(self.items) >= 2:
                self.items[item].rect.x, self.items[item].rect.y= (self.rect.x+cut_dim[0]*2/3, self.rect.y+item_dim[1]*list(self.items.keys()).index(item))
        screen.blit(self.current_sprite, (self.rect.x,self.rect.y))

    def switch_sprite(self,final:Literal["front","back","cut"]):
        if final == "front":
            self.current_sprite=self.front_sprite
        elif final == "back":
            self.current_sprite=self.back_sprite
        elif final== "cut":
            self.current_sprite=self.cut_sprite
        self.rect=self.current_sprite.get_rect()

class Item(sprite.Sprite):
    def __init__(self,name:str,cost:int,effect:Callable,sprite:Path,init_pos:Coord,cut_sprite:Path,border:Literal["blue","pink"],dimensions:Size,condition:Literal["end of turn","start of turn","on death","on hurt","on attack","when played"],uses:int):
        #ITEM INFO
        self.name=name
        self.cost=cost
        self.health=0
        self.effect=effect #a function that takes in a value and changes it appropriately
        self.border=border
        self.condition=condition #when the item activates
        self.uses=uses
        #SPRITE AND COORDS
        self.front_sprite=transform.scale(image.load(sprite),dimensions)
        self.original_sprite=sprite
        self.cut_sprite=transform.scale(image.load(cut_sprite),item_dim)
        self.back_sprite=transform.scale(image.load(cardback),card_dim)
        self.current_sprite=self.front_sprite
        self.rect=self.current_sprite.get_rect()
        self.rect.x=init_pos[0]
        self.rect.y=init_pos[1]
        self.display_rect=Rect(930,100,card_dim[0]*3,card_dim[1]*3)
        #MOVEMENT
        self.timer=0
        self.movement_phase=0
        self.destinations=[]
        self.times=[]
        self.velocity=(0,0)

    def startmove(self,dests:list[Coord],times:list[int]): #destination as a coord tuple, time in frames
        if self.timer==0: #change to accept lists of dests and coords
            self.destinations=dests
            self.times=times
            self.timer=self.times[self.movement_phase]
            self.velocity=((self.destinations[self.movement_phase][0]-self.rect.x)/self.timer, (self.destinations[self.movement_phase][1]-self.rect.y)/self.timer)

    def update(self):
        global move_hovering_over
        if self.timer!=0:
            self.rect.x+=self.velocity[0]
            self.rect.y+=self.velocity[1]
            self.timer-=1
        elif self.timer == 0 and self.movement_phase != len(self.destinations)-1 and self.destinations != []:
            self.movement_phase += 1
            self.timer=self.times[self.movement_phase]
            self.velocity=((self.destinations[self.movement_phase][0]-self.rect.x)/self.timer, (self.destinations[self.movement_phase][1]-self.rect.y)/self.timer)
        else:
            self.destinations=[]
            self.times=[]
        if attack_progressing and selected == self:
            draw.rect(screen,ORANGE,Rect(self.display_rect.left-5,self.display_rect.top-5,self.display_rect.width,self.display_rect.height),5)
        if selected == self and self.display_rect.collidepoint(mouse.get_pos()) and not attack_progressing:
            draw.rect(screen,ORANGE,Rect(self.display_rect.left-5,self.display_rect.top-5,self.display_rect.width,self.display_rect.height),5)
            move_hovering_over=(self.display_rect,self.effect)
        screen.blit(self.current_sprite, (self.rect.x,self.rect.y))

    def switch_sprite(self, final:Literal["front","back","cut"]):
        if final == "front":
            self.current_sprite=self.front_sprite
        elif final == "back":
            self.current_sprite=self.back_sprite
        elif final== "cut":
            self.current_sprite=self.cut_sprite
        self.rect=self.current_sprite.get_rect()

class Player():
    def __init__(self,name:str,player_number:int,hand_pos:Coord,field_pos:list[Coord]):
        self.name=name
        self.player_number=player_number
        self.hand=[]
        self.field: list[None|Mob]=[None,None,None]
        self.souls=1
        self.hand_pos=hand_pos
        self.field_pos=field_pos
        self.soul_colour=list(SOUL_COLOUR)
        if player_number == 1:
            self.souls_pos=(field_pos[2][0]+cut_dim[0]+10,window_dim[1]-token_dim[1]-card_dim[1])
        elif player_number == 2:
            self.souls_pos=(field_pos[2][0]+cut_dim[0]+10,50)

    def update(self):
        for i in range(len(self.hand)):
            if self.player_number==2:
                self.hand[i].switch_sprite("back")
            self.hand[i].rect.y, self.hand[i].rect.x= (self.hand_pos[1],self.hand_pos[0]+card_dim[0]*i)
            self.hand[i].update()
            #display cards
        for card in self.field:
            if card != None:
                card.update()
                draw.rect(screen,(255,0,0),Rect(card.rect.x,hearts_rails[2-self.player_number],cut_dim[0]*card.health/card.max_health,20))
                screen.blit(small_font.render(str(card.health),True,(255,255,255)),(card.rect.x+5,hearts_rails[2-self.player_number]+1))
                screen.blit(small_font.render(str(card.max_health),True,(255,255,255)),(card.rect.x-5+cut_dim[0]-round(small_font.size(str(card.max_health))[0]),hearts_rails[2-self.player_number]+1))
                if card.health <= 0:
                    if "on death" in card.passives:
                        card.passives["on_death"]()
                    if "on death" in card.items:
                        card.items["on death"]()
                    self.field[self.field.index(card)]=None
        screen.blit(soul,self.souls_pos)
        screen.blit(mjgs.render(str(self.souls),True,tuple(self.soul_colour)),(self.souls_pos[0]+token_dim[0]+5,self.souls_pos[1]-2))
        if self.player_number == 1 and markers["not enough souls"][0] != 0:
            if markers["not enough souls"][2] == 0:
                self.soul_colour[1] -= 255/markers["not enough souls"][1]/2
                self.soul_colour[2] -= 255/markers["not enough souls"][1]/2
                markers["not enough souls"][3] += 1
            elif markers["not enough souls"][2] == 1:
                self.soul_colour[1] += 255/markers["not enough souls"][1]/2
                self.soul_colour[2] += 255/markers["not enough souls"][1]/2
                markers["not enough souls"][3] += 1
            if markers["not enough souls"][3] == markers["not enough souls"][1]:
                markers["not enough souls"][3] = 0
                if markers["not enough souls"][2] == 1:
                    markers["not enough souls"][2] = 0
                elif markers["not enough souls"][2] == 0:
                    markers["not enough souls"][2] = 1
                markers["not enough souls"][0] -= 1

    def add_to_field(self,card:int,pos:int,ignore_cost:bool=False): #card is index number of hand card to take, pos is field position to take (in human number terms, not list index)
        target=self.hand.pop(card)
        if type(target) == Mob:
            self.field[pos-1]=target
            target.switch_sprite("cut")
            target.rect.x, target.rect.y=self.field_pos[pos-1]
            if not ignore_cost:
                self.souls -= target.cost
        elif type(target) == Item and self.field[pos-1] != None:
            self.field[pos-1].items[target.condition]=target
            target.switch_sprite("cut")
            if not ignore_cost:
                self.souls -= target.cost

class ClickableText():
    def __init__(self,font,text:str,colour:tuple[int,int,int],position:Coord):
        self.text=font.render(text,True,colour)
        self.textrect=self.text.get_rect()
        self.position=position
        self.textrect.x=position[0]
        self.textrect.y=position[1]

def nofunction(): #so i don't have to keep putting in checks if a move or something is None
    pass

def deckbuilder(list_to_use:dict[Card,int]) -> list[Card]:
    here_deck=[]
    for card in list_to_use:
        for i in range(list_to_use[card]):
            actual_card=eval(card)
            here_deck.append(actual_card)
    r.shuffle(here_deck)
    return here_deck

def warding_laser(**kwargs:Attack_params) -> Literal[False]:
    if kwargs["noattack"] == False:
        opp=None
        if kwargs["player"].player_number == 1:
            opp=player2
        else:
            opp=player1
        dmg=abs(opp.field.index(kwargs["target"])-kwargs["player"].field.index(kwargs["origin"]))+1
        kwargs["target"].health-=dmg
        if "on hurt" in kwargs["target"].passives:
            kwargs["target"].passives["on hurt"](origin=kwargs["origin"],target=kwargs["target"],damage=dmg)
    return False

def bite(**kwargs:Attack_params) -> Literal[True]:
    if kwargs["noattack"] == False:
        kwargs["target"].health-=2
        if "on hurt" in kwargs["target"].passives:
            kwargs["target"].passives["on hurt"](origin=kwargs["origin"],target=kwargs["target"],damage=2)
    return True

def elders_curse(**kwargs): #end of turn
    global selected
    global selected_move
    global attack_progressing
    global move_hovering_over
    if kwargs["player"] == player1:
        selected=kwargs["origin"]
        selected_move=kwargs["origin"].moveset[0]
        attack_progressing=True
        move_hovering_over=(kwargs["origin"].move_positions[0],kwargs["origin"].moveset[0])

def undead(**kwargs): #on hurt
    if kwargs["origin"].health == kwargs["origin"].max_health and kwargs["damage"] >= kwargs["origin"].health:
        kwargs["origin"].health=1

def sword_slash(**kwargs):
    kwargs["target"].health -= 1

def start_of_turn():
    for card in player1.field:
        if card != None and "start of turn" in card.passives:
            card.passives["start of turn"]()
        if card != None and "start of turn" in card.items:
            card.items["start of turn"].effect()
    for card in player2.field:
        if card != None and "start of turn" in card.passives:
            card.passives["start of turn"]()
        if card != None and "start of turn" in card.items:
            card.items["start of turn"].effect()

window_dim=(1500,850)
title_img=transform.scale(image.load("title.png"),(842,120))
card_dim=(150,225)
card_dim_rot=(225,150)
cut_dim=(169,172)
item_dim=(75,75) #get back to this, change to better value
token_dim=(30,30)
soul=transform.scale(image.load("soul.png"),token_dim)
starting_cards=5
drawing_cards=2
running=True
state="menu"
connect_state="idle"
FPS=60
clock=time.Clock()
background=transform.scale(image.load("background.png"),window_dim)
deck=[]
turn=0
subturn=1 #subturn numbers start from 1
postsubturn=1 #postsubturn numbers start from 2
cardback="card_back.png"
attack_choosing_state=False
HOST=''
PORT=6543
ORANGE = (255,180,0)
SOUL_COLOUR=(255,255,255)
sock=''
fields_anchor=(90,40)
card_spacing_x=70
card_spacing_y=50
y_rails=[fields_anchor[1],fields_anchor[1]+card_spacing_y*2+card_dim_rot[1]+cut_dim[1]]
x_rails=[fields_anchor[0],fields_anchor[0]+cut_dim[0]+card_spacing_x,fields_anchor[0]+cut_dim[0]*2+card_spacing_x*2]
hearts_rails=[y_rails[0]+cut_dim[0]+10,y_rails[1]-10-20] #0: player 2, 1: player 1
markers={"retry":False, "deck built":False, "do not connect":True, "start of turn called":False, "not enough souls":[0,0,0,0]}
selected=None #card displayed on the side
selected_move=None #move that has been selected
attack_progressing=False #is it the attack target choosing stage
move_hovering_over=None #tuple of Rect of attack being hovered over and attack function itself, used for click detection

#define cards here
#Note: cards for deck use are defined by deckbuilder(), which takes these strings and eval()s them into objects
#This is so each deck entry has a separate memory value
deck_plc=Item("Deck Placeholder",0,None,"card_back_rot.png",(100,262),"card_back_rot.png",None,card_dim_rot,'',None)
milk=r'Item("Milk",2,None,r"Sprites\Milk.png",(0,0),r"Cut Sprites\Milk.png","blue",card_dim,"when played",1)'
sword=r'Item("Sword",1,sword_slash,r"Sprites\Sword.png",(0,0),r"Cut Sprites\Sword.png","blue",card_dim,"on attack",1)'
elder=r'Mob("Elder",6,6,[],[warding_laser],{"end of turn":elders_curse},{},"aquatic","ocean","pink",r"Sprites\Elder.png",(0,0),r"Cut Sprites\Elder.png",[(987,522,1323,589)])'
zombie=r'Mob("Zombie",2,4,[],[bite],{"on hurt":undead},{},"undead","cavern","blue",r"Sprites\Zombie.png",(0,0),r"Cut Sprites\Zombie.png",[(987,512,1323,579)])'
#Mob()

decklist={zombie:15, elder:15, sword:15}
#playername=input("Enter your name: ")
playername="J1"
player1=Player(playername,1,(fields_anchor[0],y_rails[1]+cut_dim[1]+card_spacing_y),[(x_rails[0],y_rails[1]),(x_rails[1],y_rails[1]),(x_rails[2],y_rails[1])])
player2:Player=''

screen=display.set_mode(window_dim)
display.set_caption("Minecards")

font.init()
mjgs=font.Font("mojangles.ttf",40)
small_font=font.Font("mojangles.ttf",20)
beta_text=mjgs.render("Closed Beta",True,(255,100,0))
host_text=ClickableText(mjgs,"Create Game",(0,0,0),(window_dim[0]/2-mjgs.size("Create Game")[0]/2,550))
connect_text=ClickableText(mjgs,"Join Game",(0,0,0),(window_dim[0]/2-mjgs.size("Join Game")[0]/2,650))
connecting_text=mjgs.render("Waiting for connection",True,(255,0,0))
ip_enter_text=mjgs.render("Enter host IPv4",True,(0,0,0))
ip_submit_text=ClickableText(mjgs,"Connect",(0,0,0),(window_dim[0]/2-mjgs.size("Connect")[0]/2,750))
pregame_text=mjgs.render("Loading...",True,(0,0,0))
retry_text=mjgs.render("Retry Connection",True,(255,0,0))
game_plc_text=mjgs.render("Await further programming",True,(0,0,0))

while running:
    screen.blit(background,(0,0))
    if sock != '':
        read_ready, write_ready, error_ready=select.select([sock],[sock],[],0)

    for e in event.get():
        if e.type == QUIT:
            running=False
        elif e.type == MOUSEBUTTONUP:
            pos=mouse.get_pos()
            if host_text.textrect.collidepoint(pos):
                if markers["do not connect"]:
                    state="game"
                    player2=Player("Player 2",2,(fields_anchor[0],fields_anchor[1]/2-card_dim[1]+10),[(x_rails[0],y_rails[0]),(x_rails[1],y_rails[0]),(x_rails[2],y_rails[0])])
                else:
                    connect_state="hosting"
            elif connect_text.textrect.collidepoint(pos):
                connect_state="connecting"
            elif ip_submit_text.textrect.collidepoint(pos) and state == "menu" and connect_state == "connecting":
                try:
                    sock.connect((HOST,PORT))
                    state="pregame" #await info to build player2
                    print("Connection successful")
                except:
                    markers["retry"]=True

            if state == "game" and not attack_progressing:
                for card in player1.field:
                    if card != None and card.rect.collidepoint(pos):
                        selected=card
                for card in player1.hand:
                    if card.rect.collidepoint(pos):
                        selected=card
                for card in player2.field:
                    if card != None and card.rect.collidepoint(pos):
                        selected=card
                for card in player2.hand:
                    if card.rect.collidepoint(pos) and card.current_sprite != card.back_sprite:
                        selected=card
                if move_hovering_over != None:
                    if type(selected) == Mob and move_hovering_over[0].collidepoint(pos) and player1.field.index(selected) == subturn-1:
                        selected_move=move_hovering_over[1]
                        attack_progressing=True
                    if type(selected) == Item and move_hovering_over[0].collidepoint(pos):
                        selected_move=move_hovering_over[1]
                        attack_progressing=True
                for i in range(3):
                    if selected in player1.hand and player1.field[i] == None and Rect(player1.field_pos[i],cut_dim).collidepoint(pos):
                        if selected.cost <= player1.souls and type(selected) == Mob:
                            player1.add_to_field(player1.hand.index(selected),i+1)
                        else:
                            if markers["not enough souls"][0] == 0:
                                markers["not enough souls"]=[6,5,0,0] #[amount of cycles,frames per cycle,current colour,frame number]

            if attack_progressing:
                for card in player2.field:
                    if card != None and card.rect.collidepoint(pos):
                        target=card
                        counter=selected_move(origin=selected,target=target,player=player1,noattack=False)
                        other_counter=target.moveset[0](origin=target,target=selected,player=player2,noattack=True)
                        if "on attack" in selected.items:
                            card.items["on attack"].effect(origin=selected,target=target,player=player1)
                            card.items["on attack"].uses -= 1
                            if card.items["on attack"].uses == 0:
                                card.items["on attack"] = None
                        #selected.startmove([(target.rect.x,target.rect.y),(selected.rect.x,selected.rect.y)],[10,10])
                        if counter == True or counter == other_counter:
                            card.moveset[0](origin=target,target=selected,player=player2,noattack=False)
                            if "on attack" in target.items:
                                target.items["on attack"].effect(origin=target,target=selected,player=player2)
                                target.items["on attack"].uses -= 1
                                if target.items["on attack"].uses == 0:
                                    target.items["on attack"] = None
                        if postsubturn == 1:
                            subturn += 1
                        if subturn != 4:
                            selected = player1.field[subturn-1]
                        else:
                            selected=player1.field[0]
                            postsubturn += 1
                        attack_progressing=False
                        selected_move=None
                        move_hovering_over=None
                if type(selected) == Item:
                    for card in player1.field:
                        if card != None and card.rect.collidepoint(pos):
                            player1.add_to_field(player1.hand.index(selected),player1.field.index(card)+1)
                            attack_progressing=False
                            selected_move=None
                            move_hovering_over=None
                            subturn+=1
        
        elif e.type==KEYDOWN:
            if e.key==K_p:
                print(str(mouse.get_pos()))
            if connect_state == "connecting":
                if e.key == K_BACKSPACE:
                    HOST = HOST[:-1]
                else:
                    HOST += e.unicode

    if state == "menu":
        screen.blit(title_img,(window_dim[0]/2-421,165))
        screen.blit(beta_text,(window_dim[0]/2-mjgs.size("Closed Beta")[0]/2,320))
        if connect_state == "idle":
            screen.blit(host_text.text, host_text.position)
            screen.blit(connect_text.text, connect_text.position)
        elif connect_state == "hosting":
            screen.blit(connecting_text,(window_dim[0]/2-mjgs.size("Waiting for connection")[0]/2,600))
            display.update()
            sock= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            HOST="127.0.0.1"
            sock.bind((HOST,PORT))
            sock.listen()
            try: #figure out how to unblock
                sock, addr= sock.accept()
                print(f"Accepted connection at {addr}")
                state="pregame"
            except:
                pass
        elif connect_state == "connecting":
            sock= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            screen.blit(ip_enter_text, (window_dim[0]/2-mjgs.size("Enter Host IPv4")[0]/2,550))
            draw.rect(screen,(255,255,255),Rect(300,625,900,100))
            screen.blit(mjgs.render(HOST,True,(0,0,0)),(325,650))
            screen.blit(ip_submit_text.text, ip_submit_text.position)
            if markers["retry"] == True:
                screen.blit(retry_text,(window_dim[0]/2-mjgs.size("Retry Connection")[0]/2,400))

    elif state == "pregame":
        screen.blit(pregame_text,(window_dim[0]/2-mjgs.size("Loading...")[0]/2,window_dim[1]/2))
        if sock in read_ready:
            t.sleep(1)
            player2name=sock.recv(4096).decode()
            print(f"Opp. name: {player2name}")
            player2=Player(player2name,2,(fields_anchor[0],fields_anchor[1]/2),[(x_rails[0],y_rails[0]),(x_rails[1],y_rails[0]),(x_rails[2],y_rails[0])])
            state="game"
        if sock in write_ready:
            sock.send(playername.encode())

    elif state == "game":
        if markers["deck built"] == False:
            turn = 1
            deck = deckbuilder(decklist)
            for i in range(3):
                player1.hand.append(deck.pop())
                player2.hand.append(deck.pop())
                player1.add_to_field(0,i+1,True)
                player2.add_to_field(0,i+1,True)
            for i in range(starting_cards):
                player1.hand.append(deck.pop())
                player2.hand.append(deck.pop())
            markers["deck built"]=True
        if not markers["start of turn called"] and turn != 1:
            player1.souls += turn
            player2.souls += turn
            for i in range(drawing_cards):
                player1.hand.append(deck.pop())
                player2.hand.append(deck.pop())
            start_of_turn()
            markers["start of turn called"]=True
        if not markers["do not connect"]:
            screen.blit(game_plc_text,(window_dim[0]/2-mjgs.size("Await further programming")[0]/2,window_dim[1]/2))
        screen.blit(deck_plc.current_sprite,(deck_plc.rect.x,deck_plc.rect.y))
        if selected != None:
            large_image=transform.scale(image.load(selected.original_sprite),(card_dim[0]*3,card_dim[1]*3))
            test=draw.rect(screen,ORANGE,Rect(selected.rect.x-5,selected.rect.y-5,selected.rect.width+10,selected.rect.height+10),5)
            screen.blit(large_image,(930,100))
            for i in range(3):
                if player1.field[i] == None:
                    temp=Rect(player1.field_pos[i],cut_dim)
                    draw.rect(screen,ORANGE,temp,5)
                    draw.rect(screen,(255,255,255),Rect(temp.centerx-20,temp.centery-5,40,10))
                    draw.rect(screen,(255,255,255),Rect(temp.centerx-5,temp.centery-20,10,40))
        if postsubturn >= 2:
            skippost=True
            if player1.field[postsubturn-2] != None and "end of turn" in player1.field[postsubturn-2].passives:
                player1.field[postsubturn-2].passives["end of turn"](origin=player1.field[postsubturn-2],player=player1)
                skippost=False
            if player1.field[postsubturn-2] != None and "end of turn" in player1.field[postsubturn-2].items:
                player1.field[postsubturn-2].items["end of turn"].effect(origin=player1.field[postsubturn-2],player=player1)
                skippost=False
            if skippost:
                postsubturn += 1
        if postsubturn >= 4:
            subturn = 1
            postsubturn = 1
            turn += 1
            markers["start of turn called"] = False
        if postsubturn == 1:
            draw.rect(screen,(255,255,255),Rect(player1.field_pos[subturn-1][0],player1.field_pos[subturn-1][1]+cut_dim[1]+10,cut_dim[0],10))
        else:
            draw.rect(screen,(255,255,255),Rect(player1.field_pos[postsubturn-2][0],player1.field_pos[postsubturn-2][1]+cut_dim[1]+10,cut_dim[0],10))
        player1.update()
        player2.update()

    display.update()
    clock.tick(FPS)
    #print(clock.get_fps())

    '''
    To-do:
    1. Figure out how to unblock hosting socket
    2. Implement rest of gameplay loop:
        i. Select card on field (large card pops up at side), or card in hand
        ii. Select attack, or field position to place card in
        iii. Send and receive data
        iv. Action phase, you attack, opponent counters, opponent attacks, you counter. Alternatively, a card is placed
    3. Figure out animations: card going from hand to field, card attacking
    4. Add moves and passives for Mobs and effects for Items
    5. Impement combat loop and turn ends and starts
    6. Figure out why movement is so choppy
    7. Add start of turn animations
    8. Implement applying items onto mobs (works kinda)

    Sequence for adding to field:
    1. Click on card in hand: detected using card.rect.collidepoint(mouse position)
    2. The card that is clicked adds itself to selected
    3. The game loop displays whatever is selected
    4. Click on field slot: detected using rect.collidepoint(mouse position) and field slot coords
    5. If a valid slot is clicked, Player.add_to_field() is called

    Sequence for attacking:
    1. Card is automatically added to selected (as attacking goes in order)
    2. The card that is clicked adds itself to selected
    3. The game loop displays whatever is selected
    4. Hover over an attack or ability: an orange hollow rectangle appears highlighting it: detected using rect.collidepoint(mouse position) and Mob.move_positions, drawn using draw.rect(); wait, can that draw hollow rectangles?
    5. Click on move, is added to selected_move as Mob.moveset[x]: detected using collidepoint again, get index number of move_position clicked, move is that index number in moveset.
    6. attack_progressing set to True
    7. Click on a targetable Mob: detected using collidepoint again
    8. Since attack_progressing is True, this calls the function from selectied_move and passes the current Mob and original Mob as the arguments

    Passive conditions:
    "end of turn": Called at the end of the attack phase (not yet implemented)
    "start of turn": Called at the start of the turn, in the function start_of_turn()
    "on death": Called when health is 0

    Standard arguments for moves, passives, item effects, etc.:
    Callable(origin:Card that calls it, target:target card, player:player the card belongs to, noattack:only used in moves, if True only returns if it is ranged or not)
    '''