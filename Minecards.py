from pygame import *
import random as r
import time as t
import socket
import select
#Name:LAPTOP-20C14P7N, Address:172.20.57.66
#None values mean add later

class Mob(sprite.Sprite):
    def __init__(self,name,cost,health,abilities,attacks,passives,items,mob_class,biome,border,sprite,init_pos,cut_sprite,move_positions):
        super().__init__()
        #MOB INFO
        self.name=name
        self.cost=cost
        self.health=health
        #passives listed first on card, then attacks, then abilities
        self.abilities=abilities 
        self.passives=passives #dict, index is a trigger marker which allows functions to know when to call it, same for items
        self.moveset=attacks + abilities #used for finding which one was clicked
        self.move_positions=move_positions #hitboxes of moves, in order
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
        self.timer=0
        self.velocity=(0,0)

    def startmove(self,dest,time): #destination as a coord tuple, time in frames
        if self.timer==0:
            self.dest=dest
            self.timer=time
            self.velocity=((dest[0]-self.rect.x)/time, (dest[1]-self.rect.y)/time)

    def update(self):
        if self.timer!=0:
            self.rect.x+=self.velocity[0]
            self.rect.y+=self.velocity[1]
            self.timer-=1
        screen.blit(self.current_sprite, (self.rect.x,self.rect.y))

    def switch_sprite(self,final):
        if final == "front":
            self.current_sprite=self.front_sprite
        elif final == "back":
            self.current_sprite=self.back_sprite
        elif final== "cut":
            self.current_sprite=self.cut_sprite
        self.rect=self.current_sprite.get_rect()

class Item(sprite.Sprite):
    def __init__(self,name,cost,effect,sprite,init_pos,cut_sprite,border,dimensions):
        #ITEM INFO
        self.name=name
        self.cost=cost
        self.effect=effect #a function that takes in a value and changes it appropriately
        self.border=border
        #SPRITE AND COORDS
        self.front_sprite=transform.scale(image.load(sprite),dimensions)
        self.original_sprite=sprite
        self.cut_sprite=transform.scale(image.load(cut_sprite),item_dim)
        self.back_sprite=transform.scale(image.load(cardback),card_dim)
        self.current_sprite=self.front_sprite
        self.rect=self.current_sprite.get_rect()
        self.rect.x=init_pos[0]
        self.rect.y=init_pos[1]
        #MOVEMENT
        self.timer=0
        self.velocity=(0,0)

    def startmove(self,dest,time): #destination as a coord tuple, time in frames
        if self.timer==0:
            self.dest=dest
            self.timer=time
            self.velocity=((dest[0]-self.rect.x)/time, (dest[1]-self.rect.y)/time)

    def update(self):
        if self.timer!=0:
            self.rect.x+=self.velocity[0]
            self.rect.y+=self.velocity[1]
            self.timer-=1
        screen.blit(self.current_sprite, (self.rect.x,self.rect.y))

    def switch_sprite(self, final):
        if final == "front":
            self.current_sprite=self.front_sprite
        elif final == "back":
            self.current_sprite=self.back_sprite
        elif final== "cut":
            self.current_sprite=self.cut_sprite
        self.rect=self.current_sprite.get_rect()


class Player():
    def __init__(self,name,player_number,hand_pos,field_pos):
        self.name=name
        self.player_number=player_number
        self.hand=[]
        self.field={1:None, 2:None, 3:None}
        self.souls=0
        self.hand_pos=hand_pos
        self.field_pos=field_pos

    def update(self):
        for i in range(len(self.hand)):
            self.hand[i].rect.y, self.hand[i].rect.x= (self.hand_pos[1],self.hand_pos[0]+card_dim[0]*i)
            self.hand[i].update()
            #display cards
        for card in self.field:
            if self.field[card] != None:
                self.field[card].update()

    def add_to_field(self,card,pos): #card is index number of hand card to take, pos is field position to take
        target=self.hand.pop(card)
        self.field[pos]=target
        target.switch_sprite("cut")
        target.rect.x, target.rect.y=self.field_pos[pos-1]

class ClickableText():
    def __init__(self,font,text,colour,position):
        self.text=font.render(text,True,colour)
        self.textrect=self.text.get_rect()
        self.position=position
        self.textrect.x=position[0]
        self.textrect.y=position[1]

def deckbuilder(list_to_use):
    here_deck=[]
    for card in list_to_use:
        for i in range(list_to_use[card]):
            actual_card=eval(card)
            here_deck.append(actual_card)
    r.shuffle(here_deck)
    return here_deck


window_dim=(1500,850)
title_img=transform.scale(image.load("title.png"),(842,120))
card_dim=(150,225)
card_dim_rot=(225,150)
cut_dim=(169,172)
item_dim=(150,150) #get back to this, change to better value
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
cardback="card_back.png"
attack_choosing_state=False
HOST=''
PORT=6543
sock=''
fields_anchor=(90,40)
card_spacing_x=70
card_spacing_y=50
y_rails=[fields_anchor[1],fields_anchor[1]+card_spacing_y*2+card_dim_rot[1]+cut_dim[1]]
x_rails=[fields_anchor[0],fields_anchor[0]+cut_dim[0]+card_spacing_x,fields_anchor[0]+cut_dim[0]*2+card_spacing_x*2]
markers={"retry":False, "deck built":False, "do not connect":True}
selected=None
selected_move=None
attack_progressing=False

#define cards here
#Note: cards for deck use are defined by deckbuilder(), which takes these strings and eval()s them into objects
#This is so each deck entry has a separate memory value
deck_plc=Item("Deck Placeholder",0,None,"card_back_rot.png",(100,262),"card_back_rot.png",None,card_dim_rot)
milk=r'Item("Milk",2,None,r"Sprites\Milk.png",(0,0),r"Cut Sprites\Milk.png","blue",card_dim)'
elder=r'Mob("Elder",6,6,[],[],[],[],"aquatic","ocean","pink",r"Sprites\Elder.png",(0,0),r"Cut Sprites\Elder.png",None)'

decklist={milk:20, elder:20}
#playername=input("Enter your name: ")
playername="J1"
player1=Player(playername,1,(fields_anchor[0],y_rails[1]+cut_dim[1]+card_spacing_y),[(x_rails[0],y_rails[1]),(x_rails[1],y_rails[1]),(x_rails[2],y_rails[1])])
player2=''

screen=display.set_mode(window_dim)
display.set_caption("Minecards")

font.init()
font=font.Font("mojangles.ttf",40)
beta_text=font.render("Closed Beta",True,(255,100,0))
host_text=ClickableText(font,"Create Game",(0,0,0),(window_dim[0]/2-font.size("Create Game")[0]/2,550))
connect_text=ClickableText(font,"Join Game",(0,0,0),(window_dim[0]/2-font.size("Join Game")[0]/2,650))
connecting_text=font.render("Waiting for connection",True,(255,0,0))
ip_enter_text=font.render("Enter host IPv4",True,(0,0,0))
ip_submit_text=ClickableText(font,"Connect",(0,0,0),(window_dim[0]/2-font.size("Connect")[0]/2,750))
pregame_text=font.render("Loading...",True,(0,0,0))
retry_text=font.render("Retry Connection",True,(255,0,0))
game_plc_text=font.render("Await further programming",True,(0,0,0))

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
                    player2=Player("Player 2",2,(fields_anchor[0],fields_anchor[1]/2),[(x_rails[0],y_rails[0]),(x_rails[1],y_rails[0]),(x_rails[2],y_rails[0])])
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

            if state == "game":
                for card in player1.field:
                    if player1.field[card] != None and player1.field[card].rect.collidepoint(pos):
                        selected=player1.field[card]
                for card in player1.hand:
                    if card.rect.collidepoint(pos):
                        selected=card
                for card in player2.field:
                    if player2.field[card] != None and player2.field[card].rect.collidepoint(pos):
                        selected=player2.field[card]
                for card in player2.hand:
                    if card.rect.collidepoint(pos):
                        selected=card
        
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
        screen.blit(beta_text,(window_dim[0]/2-font.size("Closed Beta")[0]/2,320))
        if connect_state == "idle":
            screen.blit(host_text.text, host_text.position)
            screen.blit(connect_text.text, connect_text.position)
        elif connect_state == "hosting":
            screen.blit(connecting_text,(window_dim[0]/2-font.size("Waiting for connection")[0]/2,600))
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
            screen.blit(ip_enter_text, (window_dim[0]/2-font.size("Enter Host IPv4")[0]/2,550))
            draw.rect(screen,(255,255,255),Rect(300,625,900,100))
            screen.blit(font.render(HOST,True,(0,0,0)),(325,650))
            screen.blit(ip_submit_text.text, ip_submit_text.position)
            if markers["retry"] == True:
                screen.blit(retry_text,(window_dim[0]/2-font.size("Retry Connection")[0]/2,400))

    elif state == "pregame":
        screen.blit(pregame_text,(window_dim[0]/2-font.size("Loading...")[0]/2,window_dim[1]/2))
        if sock in read_ready:
            t.sleep(1)
            player2name=sock.recv(4096).decode()
            print(f"Opp. name: {player2name}")
            player2=Player(player2name,2,(fields_anchor[0],fields_anchor[1]/2),[(x_rails[0],y_rails[0]),(x_rails[1],y_rails[0]),(x_rails[2],y_rails[0])])
            state="game"
        if sock in write_ready:
            sock.send(playername.encode())

    elif state == "game":
        if not markers["do not connect"]:
            screen.blit(game_plc_text,(window_dim[0]/2-font.size("Await further programming")[0]/2,window_dim[1]/2))
        if markers["deck built"] == False:
            deck = deckbuilder(decklist)
            for i in range(3):
                player1.hand.append(deck.pop())
                player1.hand.append(deck.pop())
                player2.hand.append(deck.pop())
                player2.hand.append(deck.pop())
                player1.add_to_field(0,i+1)
                player2.add_to_field(0,i+1)
            markers["deck built"]=True
        screen.blit(deck_plc.current_sprite,(deck_plc.rect.x,deck_plc.rect.y))
        if selected != None:
            large_image=transform.scale(image.load(selected.original_sprite),(card_dim[0]*3,card_dim[1]*3))
            screen.blit(large_image,(930,100))
        player1.update()
        player2.update()

    display.update()
    clock.tick(FPS)

    '''
    To-do:
    1. Figure out how to unblock hosting socket
    2. Display cards in hand (works, code in different display for player 2)
    3. Implement rest of gameplay loop:
        i. Select card on field (large card pops up at side), or card in hand
        ii. Select attack, or field position to place card in
        iii. Send and receive data
        iv. Action phase, you attack, opponent counters, opponent attacks, you counter. Alternatively, a card is placed
    4. Figure out animations: card going from hand to field, card attacking
    5. Implement health and souls, decide where they're going to go
    6. Add moves and passives for Mobs and effects for Items

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
    8. Since attack_progressing is True, this calls the function from selectied_move and passes the current Mob as the argument
    '''