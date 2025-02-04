#SECTION: Import -----------------------------------------------------------------------------------------------------------
import os
import random as r
import time as t
from pygame import *

#SECTION: Classes and Functions --------------------------------------------------------------------------------------------
class Mob(sprite.Sprite):
    def __init__(self,name,cost,health,ability,attacks,items,mobclass,biome,status,border,description,sprite,size,init_pos):
        super().__init__()
        self.name=name #str
        self.cost=cost #int
        self.health=health #int
        self.ability=ability #list of func
        self.attacks=attacks #list of func
        self.items=items #list of obj
        self.mobclass=mobclass #str
        self.biome=biome #str
        self.status=status #list of str
        self.border=border #str
        self.description=description #str
        self.frontsprite=transform.scale(image.load(sprite),size) #internal, holds the front art
        self.backsprite=transform.scale(image.load(var.cardback),size) #internal, holds the back art
        self.currentsprite=self.frontsprite #internal, decides whether the front or back art shows
        self.rect=self.sprite.get_rect() #internal
        self.rect.x=init_pos[0] #internal, x position
        self.rect.y=init_pos[1] #internal, y position

    def invisible(self):
        self.currentsprite=self.backsprite
        self.rect=self.backsprite.get_rect()

    def visible(self):
        self.currentsprite=self.frontsprite
        self.rect=self.frontsprite.get_rect()

    def moveto(self,dest,angle,time):
        pass

    def attack(self,target,attack_num):
        pass

    def update(self):
        screen.blit(self.currentsprite,(self.rect.x,self.rect.y))

class Item(sprite.Sprite):
    def __init__(self,name,cost,effect,description,sprite,size,init_pos):
        super().__init__()
        self.name=name #str
        self.cost=cost #int
        self.effect=effect #func
        self.frontsprite=transform.scale(image.load(sprite),size) #internal
        self.backsprite=transform.scale(image.load(var.cardback),size)
        self.currentsprite=self.frontsprite
        self.rect=self.frontsprite.get_rect() #internal
        self.rect.x=init_pos[0] #internal, x position
        self.rect.y=init_pos[1] #internal, y position

    def invisible(self):
        self.currentsprite=self.backsprite
        self.rect=self.backsprite.get_rect()

    def visible(self):
        self.currentsprite=self.frontsprite
        self.rect=self.frontsprite.get_rect()

    def moveto(self,dest):
        self.rect.x=dest[0]
        self.rect.y=dest[1]

    def update(self):
        screen.blit(self.currentsprite,(self.rect.x,self.rect.y))

class Player():
    def __init__(self,playernum,name,hand,field,points,init_cards,hand_pos,units_pos):
        self.playernum=playernum #int, which player is this
        self.name=name #str
        self.hand=hand #list of obj. Empty at first.
        self.field=field #list of obj
        for i in range(init_cards):
            hand.append(var.deck.pop())
        self.points=points
        self.hand_pos=hand_pos #coordinate tuple
        self.units_pos=units_pos #list of coordinate tuple

    def hide_cards(self):
        for i in range(len(self.hand)):
            self.hand[i].invisible()
            self.hand[i].moveto((self.hand_pos[0]+(var.carddimensions[0])*i,self.hand_pos[1]))
            self.hand[i].update()

    def show_cards(self):
        for i in range(len(self.hand)):
            self.hand[i].visible()
            self.hand[i].moveto((self.hand_pos[0]+(var.carddimensions[0])*i,self.hand_pos[1]))
            self.hand[i].update()

    def update(self):
        if var.turn==self.playernum:
            self.show_cards()
        else:
            self.hide_cards()
        #updates for self

def deckbuilder():
    var.deck=[]
    var.deckname=[]
    for card in var.decklist:
        for i in range(var.decklist[card]):
            var.deck.append(card)
            var.deckname.append(card.name)
    r.shuffle(var.deck)
    print(var.deckname)

def apply(target,item):
    target.items.append(item)

#os.system("cls") to clear console

#SECTION: Variables --------------------------------------------------------------------------------------------------------
class Game():
    def __init__(self):
        self.width=1500
        self.height=850
        self.carddimensions=(150,225) #aspect ratio: 2:3
        self.starting_cards=5
        self.drawing_cards=2
        self.running=True
        self.finished=False
        self.FPS=60
        self.clock=time.Clock()
        self.background=transform.scale(image.load(r"C:\Users\User\OneDrive\Desktop\Minecards\background.png"),(self.width,self.height))
        self.decklist={}
        self.deck=[]
        self.deckname=[]
        self.turn=0
        self.turnnum=0
        self.cardback=r"C:\Users\User\OneDrive\Desktop\Minecards\card_back.png"
        self.units_align_x=self.width/4 # card alignment, vertical lines
        self.units_align_y=self.height/3 # card alignment, horizontal lines
        self.playing=True
display.init()
var=Game()

shield=Item("Shield",2,None,"A shield.",r"C:\Users\User\OneDrive\Desktop\Minecards\Shield.png",var.carddimensions,(0,0))

#r"C:\Users\User\OneDrive\Desktop\Minecards\xxx.yyy"

var.decklist={shield:40}
player1name=input("Input player 1's name -> ")
player2name=input("Input player 2's name -> ")
deckbuilder()
player1=Player(1,player1name,[],[],0,var.starting_cards,(5,5),[(var.units_align_x,var.units_align_y),(var.units_align_x*2,var.units_align_y),(var.units_align_x*3,var.units_align_y)])
player2=Player(2,player2name,[],[],0,var.starting_cards,(5,var.height-5-var.carddimensions[1]),[(var.units_align_x,var.units_align_y*2),(var.units_align_x*2,var.units_align_y*2),(var.units_align_x*3,var.units_align_y*2)])
screen=display.set_mode((var.width,var.height))
screen.blit(var.background,(0,0))
display.set_caption("Minecards")
print(os.getcwd())

font.init()
font=font.SysFont("Times New Roman",40)
player1tag=font.render(player1name,True,(200,200,200))
player2tag=font.render(player2name,True,(200,200,200))

#SECTION: Game Loop --------------------------------------------------------------------------------------------------------
while var.running:
    for e in event.get():
        if e.type==QUIT:
            var.running=False
        elif e.type==KEYDOWN:
            if e.key==K_p:
                print(str(mouse.get_pos()))
            if e.key==K_s:
                if var.turn==1:
                    var.turn=2
                if var.turn==2:
                    var.turn=1
        elif e.type==MOUSEBUTTONDOWN:
            #x,y=event.pos()
            if var.turn==1:
                pass
            if var.turn==2:
                pass

    if var.playing:
        var.turn=1
        screen.blit(player1tag,(5,10+var.carddimensions[1]))
        screen.blit(player2tag,(5,var.height-var.carddimensions[1]-10))
        player1.update()
        player2.update()

    display.update()
    var.clock.tick(var.FPS)
