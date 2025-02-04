from pygame import *
import socket
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
        self.front_sprite=transform.scale(image.load(sprite),var.card_dim)
        self.cut_sprite=transform.scale(image.load(cut_sprite),var.cut_dim)
        self.back_sprite=transform.scale(image.load(var.cardback),var.card_dim)
        self.current_sprite=self.front_sprite
        self.rect=self.sprite.get_rect()
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
        screen.blit(self.image, (self.rect.x,self.rect.y))

    def switch_sprite(self):
        if self.current_sprite==self.front_sprite:
            self.current_sprite=self.back_sprite

        elif self.current_sprite==self.back_sprite:
            self.current_sprite=self.front_sprite

class Item(sprite.Sprite):
    def __init__(self,name,cost,effect,sprite,init_pos,cut_sprite):
        #ITEM INFO
        self.name=name
        self.cost=cost
        self.effect=effect #a function that takes in a value and changes it appropriately
        #SPRITE AND COORDS
        self.front_sprite=transform.scale(image.load(sprite),var.card_dim)
        self.cut_sprite=transform.scale(image.load(cut_sprite),var.item_dim)
        self.back_sprite=transform.scale(image.load(var.cardback),var.card_dim)
        self.current_sprite=self.front_sprite
        self.rect=self.sprite.get_rect()
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
        screen.blit(self.image, (self.rect.x,self.rect.y))

    def switch_sprite(self):
        if self.current_sprite==self.front_sprite:
            self.current_sprite=self.back_sprite

        elif self.current_sprite==self.back_sprite:
            self.current_sprite=self.front_sprite

class Player():
    def __init__(self,name,player_number,hand,souls,hand_pos,units_pos):
        self.name=name
        self.player_number=player_number
        self.hand=hand
        self.field={1:None, 2:None, 3:None}
        self.souls=souls
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

class Game():
    def __init__(self):
        self.window_dim=(1500,850)
        self.card_dim=(150,225)
        self.cut_dim=None
        self.item_dim=None
        self.starting_cards=5
        self.drawing_cards=2
        self.running=True
        self.state="menu"
        self.connect_state="idle"
        self.FPS=60
        self.clock=time.Clock()
        self.background=transform.scale(image.load(r"C:\Users\User\OneDrive\Desktop\Minecards\background.png"),self.window_dim)
        self.decklist={}
        self.deck=[]
        self.deck_name=[]
        self.turn=0
        self.which_player=0
        self.cardback=r"C:\Users\User\OneDrive\Desktop\Minecards\card_back.png"
        self.units_align_x=None
        self.units_align_y=None
        self.attack_choosing_state=False
        self.HOST=''
        self.PORT=65432
        self.sock=''

var=Game()
screen=display.set_mode(var.window_dim)
display.set_caption("Minecards")

font.init()
cour=font.Font(r"C:\Users\User\OneDrive\Desktop\Minecards\Shooter (Reference)\cour.ttf",40)
font_large=font.Font(r"C:\Users\User\OneDrive\Desktop\Minecards\mojangles.ttf",120)
font=font.Font(r"C:\Users\User\OneDrive\Desktop\Minecards\mojangles.ttf",40)
title_text=font_large.render("Minecards",True,(200,200,200))
beta_text=font.render("Closed Beta",True,(200,200,200))
host_text=ClickableText(font,"Create Game",(0,0,0),(var.window_dim[0]/2-font.size("Create Game")[0]/2,550))
connect_text=ClickableText(font,"Join Game",(0,0,0),(var.window_dim[0]/2-font.size("Join Game")[0]/2,650))
connecting_text=font.render("Waiting for connection",True,(255,0,0))
ip_enter_text=font.render("Enter host IPv4",True,(0,0,0))
ip_submit_text=ClickableText(font,"Connect",(0,0,0),(var.window_dim[0]/2-font.size("Connect")[0]/2,750))
pregame_text=font.render("Await further programming",True,(0,0,0))

while var.running:
    screen.blit(var.background,(0,0))

    for e in event.get():
        if e.type == QUIT:
            var.running=False
        elif e.type == MOUSEBUTTONUP:
            pos=mouse.get_pos()
            if host_text.textrect.collidepoint(pos):
                var.connect_state="hosting"
            elif connect_text.textrect.collidepoint(pos):
                var.connect_state="connecting"
            elif ip_submit_text.textrect.collidepoint(pos) and var.state == "menu" and var.connect_state == "connecting":
                try:
                    var.sock.connect((var.HOST,var.PORT))
                    accept=var.sock.recv(4096)
                    print(accept)
                    var.state="pregame" #await info to build player2
                except:
                    print("Connection Failed")
        elif e.type==KEYDOWN:
            if e.key==K_p:
                print(str(mouse.get_pos()))
            if var.connect_state == "connecting":
                if e.key == K_BACKSPACE:
                    var.HOST = var.HOST[:-1]
                else:
                    var.HOST += e.unicode

    if var.state == "menu":
        screen.blit(title_text,(var.window_dim[0]/2-font_large.size("Minecards")[0]/2,200))
        screen.blit(beta_text,(var.window_dim[0]/2-font.size("Closed Beta")[0]/2,320))
        if var.connect_state == "idle":
            screen.blit(host_text.text, host_text.position)
            screen.blit(connect_text.text, connect_text.position)
        elif var.connect_state == "hosting":
            screen.blit(connecting_text,(var.window_dim[0]/2-font.size("Waiting for connection")[0]/2,600))
            display.update()
            var.sock= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            var.HOST="127.0.0.1"
            var.sock.bind((var.HOST,var.PORT))
            var.sock.listen()
            var.sock.setblocking(False)
            try:
                var.sock, addr= var.sock.accept()
                var.state=="pregame"
            except:
                pass
        elif var.connect_state == "connecting":
            var.sock= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            screen.blit(ip_enter_text, (var.window_dim[0]/2-font.size("Enter Host IPv4")[0]/2,550))
            draw.rect(screen,(255,255,255),Rect(300,625,900,100))
            screen.blit(font.render(var.HOST,True,(0,0,0)),(325,650))
            screen.blit(ip_submit_text.text, ip_submit_text.position)

    elif var.state == "pregame":
        screen.blit(pregame_text,(var.window_dim[0]/2-font.size("Await further programming")[0]/2,var.window_dim[1]/2))

    elif var.state == "game":
        player1.update()
        player2.update()

    display.update()
    var.clock.tick(var.FPS)