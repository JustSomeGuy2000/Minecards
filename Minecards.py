from pygame import *
import random as r
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
        #on click, detect which move position it falls under, get index number of that, get move from moveset
        self.items=items
        self.mob_class=mob_class
        self.biome=biome
        self.status={"psn":0,"frz":0,"fire":0}
        self.border=border #blue or pink
        #SPRITE AND COORDS
        self.front_sprite=transform.scale(image.load(sprite),card_dim)
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

    def update(self, screen):
        if self.timer!=0:
            self.rect.x+=self.velocity[0]
            self.rect.y+=self.velocity[1]
            self.timer-=1
        screen.blit(self.image, (self.rect.x,self.rect.y))

    def switch_sprite(self):
        if self.current_sprite==self.front_sprite:
            self.current_sprite=self.back_sprite
            self.rect=self.current_sprite.get_rect()

        elif self.current_sprite==self.back_sprite:
            self.current_sprite=self.front_sprite
            self.rect=self.current_sprite.get_rect()

class Item(sprite.Sprite):
    def __init__(self,name,cost,effect,sprite,init_pos,cut_sprite,border):
        #ITEM INFO
        self.name=name
        self.cost=cost
        self.effect=effect #a function that takes in a value and changes it appropriately
        self.border=border
        #SPRITE AND COORDS
        self.front_sprite=transform.scale(image.load(sprite),card_dim)
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

    def update(self, screen):
        if self.timer!=0:
            self.rect.x+=self.velocity[0]
            self.rect.y+=self.velocity[1]
            self.timer-=1
        screen.blit(self.image, (self.rect.x,self.rect.y))

    def switch_sprite(self):
        if self.current_sprite==self.front_sprite:
            self.current_sprite=self.back_sprite
            self.rect=self.current_sprite.get_rect()

        elif self.current_sprite==self.back_sprite:
            self.current_sprite=self.front_sprite
            self.rect=self.current_sprite.get_rect()

class Player():
    def __init__(self,name,player_number,hand_pos,units_pos):
        self.name=name
        self.player_number=player_number
        self.hand=[]
        self.field={1:None, 2:None, 3:None}
        self.souls=0
        self.hand_pos=hand_pos
        self.units_pos=units_pos

    def update(self):
        for card in self.hand:
            card.update()

class ClickableText():
    def __init__(self,font,text,colour,position):
        self.text=font.render(text,True,colour)
        self.textrect=self.text.get_rect()
        self.position=position
        self.textrect.x=position[0]
        self.textrect.y=position[1]

def deckbuilder():
    deck=[]
    deckname=[]
    for card in decklist:
        for i in range(decklist[card]):
            deck.append(card)
            deckname.append(card.name)
    r.shuffle(deck)
    print(deckname)


window_dim=(1500,850)
card_dim=(150,225)
cut_dim=(225,230)
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
deck_name=[]
turn=0
which_player=0
cardback="card_back.png"
units_align_x=None
units_align_y=None
attack_choosing_state=False
HOST=''
PORT=6543
sock=''
markers={"retry":False, "deck built":False}

#define cards here
milk=Item("Milk",2,None,r"Sprites\Milk.png",(0,0),r"Cut Sprites\Milk.png","blue")

decklist={milk:40}
#playername=input("Enter your name: ")
playername="J1"
player1=Player(playername,1,None,None)
player2=''

screen=display.set_mode(window_dim)
display.set_caption("Minecards")

font.init()
font_large=font.Font("mojangles.ttf",120)
font=font.Font("mojangles.ttf",40)
title_text=font_large.render("Minecards",True,(200,200,200))
beta_text=font.render("Closed Beta",True,(200,200,200))
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
                connect_state="hosting"
            elif connect_text.textrect.collidepoint(pos):
                connect_state="connecting"
            elif ip_submit_text.textrect.collidepoint(pos) and state == "menu" and connect_state == "connecting":
                try:
                    sock.connect((HOST,PORT))
                    state="pregame" #await info to build player2
                except:
                    markers["retry"]=True
        elif e.type==KEYDOWN:
            if e.key==K_p:
                print(str(mouse.get_pos()))
            if connect_state == "connecting":
                if e.key == K_BACKSPACE:
                    HOST = HOST[:-1]
                else:
                    HOST += e.unicode

    if state == "menu":
        screen.blit(title_text,(window_dim[0]/2-font_large.size("Minecards")[0]/2,200))
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
            read_ready, write_ready, error_ready=select.select([sock],[sock],[],0)
            #try:
            if sock in read_ready:
                sock, addr= sock.accept()
                print(f"Accepted connection at {addr}")
                state="pregame"
            #except:
                #pass
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
            player2name=sock.recv(4096).decode()
            player2=Player(player2name,2,None,None)
            state="game"
        if sock in write_ready:
            sock.send(playername.encode())

    elif state == "game":
        screen.blit(game_plc_text,(window_dim[0]/2-font.size("Await further programming")[0]/2,window_dim[1]/2))
        if markers["deck built"] == False:
            deckbuilder()
            markers["deck built"]=True
        player1.update()
        player2.update()

    display.update()
    clock.tick(FPS)