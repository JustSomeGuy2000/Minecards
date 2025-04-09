from __future__ import annotations
from collections.abc import Callable
from typing import Literal
from shutil import rmtree
from math import copysign
from random import *
from pygame import *
import traceback as t
import binascii as b
import time as tm
import socket
import select
import stat
import copy
import json
import sys
import os

type Card = Mob|Item
type Coord = tuple[int|float,int|float]
type Size = tuple[int,int]
type Path = str
type Attack_params = dict[Literal["origin"]:Card,Literal["target"]:Card,Literal["damage"]:int,Literal["noattack"]:bool]

window_dim=(1500,850)
screen=display.set_mode(window_dim)
display.set_caption("Minecards")
font.init()
mjgs=font.Font(r"Assets\mojangles.ttf",40)
small_font=font.Font(r"Assets\mojangles.ttf",20)
large_font=font.Font(r"Assets\mojangles.ttf",80)

class Mob(sprite.Sprite):
    def __init__(self,name:str,cost:int,health:int,abilities:list[Ability],attacks:list[Callable],passives:dict[Literal["end of turn","start of turn","on death","on hurt","on attack","when played","on this turn","always","end this turn"],Callable],items:dict[Literal["end of turn","start of turn","on death","on hurt","on attack","when played","on this turn"],list[Item]],mob_class:Literal["undead","arthropod","aquatic","human","misc"],biome:Literal["plains","cavern","ocean","swamp"],border:Literal["blue","pink"],sprite:Path,init_pos:Coord,cut_sprite:Path,move_positions:list[tuple[int,int,int,int]],id_num:int=0,**kwargs):
        super().__init__()
        #MOB INFO
        self.name=name
        self.cost=cost
        self.health=health
        self.max_health=health
        self.original_health=health
        #passives listed first on card, then attacks, then abilities. Very important for detection
        self.abilities=abilities 
        self.passives=passives #dict, index is a trigger marker which allows functions to know when to call it, same for items
        self.moveset=attacks #attacks
        self.move_positions:list[Rect]=[]
        for position in move_positions:
            self.move_positions.append(Rect(position[0]+large_image_pos[0],position[1]+large_image_pos[1],position[2]-position[0],position[3]-position[1]))#hitboxes of moves, in order
        self.items=items
        self.mob_class=mob_class
        self.biome=biome
        self.status={"psn":0,"aquatised":0}
        self.border=border #blue or pink
        self.miscs=kwargs
        self.original_miscs=kwargs
        self.id_num:int=id_num
        self.proxy_for:Mob|None=None
        self.proxy:Mob|None=None
        self.owned_by:Player=None
        self.playable:bool=True
        #SPRITE AND COORDS
        self.front_sprite=transform.scale(image.load(sprite),card_dim).convert()
        self.original_sprite=sprite
        self.cut_sprite=transform.scale(image.load(cut_sprite),cut_dim).convert()
        self.back_sprite=cardback
        self.current_sprite=self.front_sprite
        self.rect=self.current_sprite.get_rect()
        self.rect.x=init_pos[0]
        self.rect.y=init_pos[1]
        self.shade=Surface(card_dim).convert_alpha()
        self.shade.fill((0,0,0,128))
        #MOVEMENT
        self.movement_phase=0 #indicates which location is currently being moved to
        self.destinations=[] #the list of locations to move to, in order
        self.times=[]
        self.timer=0
        self.velocity=(0,0)
        self.hurt_timer=0
        self.hurt_surface=None
        self.hurt_anchor=None
        self.internal_coords=[init_pos[0],init_pos[1]]
        self.rot=[0,0,0] #frames to rotate, final rotation angle, current frame
        self.rot_sprite=None
        self.move_anim:tuple[int,Surface,Coord]=(0,None,None)

    def __repr__(self):
        temp="None"
        if self.owned_by == player1:
            temp="Player 1"
            if self in player1.hand:
                temp2="hand"
            else:
                temp2="field"
        elif self.owned_by == player2:
            temp="Player 2"
            if self in player2.hand:
                temp2="hand"
            else:
                temp2="field"
        return f"<Mob {self.name} in {temp}'s {temp2}>"

    def startmove(self,dests:list[Coord],times:list[int]):
        if self.timer != 0 or (len(self.destinations) > 0 and self.times[-1] == 0):
            self.destinations+=dests
            self.times+=times
        else:
            self.destinations=dests
            self.times=times
            self.movement_phase=0
            self.timer=self.times[self.movement_phase]
            if self.timer != 0:
                self.velocity=((self.destinations[self.movement_phase][0]-self.internal_coords[0])/self.timer, (self.destinations[self.movement_phase][1]-self.internal_coords[1])/self.timer)

    def startrot(self,angle:int,rot_time:int):
        if self.rot[2] == 0:
            if rot_time > 0:
                self.rot=[rot_time,angle,0]
            else:
                self.current_sprite=transform.rotate(self.current_sprite,angle)

    def update(self):
        global move_hovering_over
        global setup
        if (self.owned_by.souls < self.cost or None not in self.owned_by.field) and self in self.owned_by.hand:
            self.playable=False
        else:
            self.playable=True
        if cardback != self.back_sprite:
            self.back_sprite=cardback
        if self.timer!=0:
            self.internal_coords[0]+=self.velocity[0]
            self.internal_coords[1]+=self.velocity[1]
            self.timer-=1
        elif self.timer == 0 and self.movement_phase != len(self.destinations)-1 and self.destinations != [] and self.times[self.movement_phase+1] == 0:
            self.movement_phase+=1
            self.internal_coords[0], self.internal_coords[1]=self.destinations[self.movement_phase]
            self.timer=self.times[self.movement_phase]
        elif self.timer == 0 and self.movement_phase != len(self.destinations)-1 and self.destinations != [] and self.times[0] == 0 and self.movement_phase == 0:
            self.internal_coords[0], self.internal_coords[1]=self.destinations[self.movement_phase]
            self.movement_phase+=1
            self.timer=self.times[self.movement_phase]
            self.velocity=((self.destinations[self.movement_phase][0]-self.internal_coords[0])/self.timer, (self.destinations[self.movement_phase][1]-self.internal_coords[1])/self.timer)
        elif self.timer == 0 and self.movement_phase != len(self.destinations)-1 and self.destinations != []:
            self.movement_phase+=1
            self.timer=self.times[self.movement_phase]
            self.velocity=((self.destinations[self.movement_phase][0]-self.internal_coords[0])/self.timer, (self.destinations[self.movement_phase][1]-self.internal_coords[1])/self.timer)
        else:
            self.destinations=[]
            self.times=[]
            self.movement_phase=0
        if self.rot[2] == self.rot[0] and self.rot[0] != 0:
            self.current_sprite=transform.rotate(self.current_sprite,self.rot[1])
            self.rot=[0,0,0]
        elif self.rot[0] != 0:
            self.rot_sprite=transform.rotate(self.current_sprite,self.rot[1]/self.rot[0]*self.rot[2])
            self.rot[2]+=1
        self.rect.x, self.rect.y=int(self.internal_coords[0]), int(self.internal_coords[1])
        if self.rot[2] != self.rot[0]:
            screen.blit(self.rot_sprite,(self.rect.x,self.rect.y))
        else:
            screen.blit(self.current_sprite, (self.rect.x,self.rect.y))
        if not self.playable and self.owned_by == player1:
            screen.blit(self.shade,(self.rect.x,self.rect.y))
        for item in self.items:
            for subitem in self.items[item]:
                if subitem.times == []:
                    if len(denest(self.items)) <= 2:
                        subitem.internal_coords[0], subitem.internal_coords[1]= (self.rect.x+cut_dim[0]*2/3, self.rect.y+item_dim[1]*denest(self.items).index(subitem))
                    else:
                        subitem.internal_coords[0], subitem.internal_coords[1]= (self.rect.x+cut_dim[0]*2/3, self.rect.y+cut_dim[1]*(denest(self.items).index(subitem)/len(denest(self.items))))
                subitem.update()

    def switch_sprite(self,final:Literal["front","back","cut"]):
        if final == "front":
            self.current_sprite=self.front_sprite
        elif final == "back":
            self.current_sprite=self.back_sprite
        elif final== "cut":
            self.current_sprite=self.cut_sprite
        self.rect=self.current_sprite.get_rect()

    def heal(self,value):
        if (self.health + value) <= self.max_health:
            self.health += value
        else:
            self.health = self.max_health

    def reset(self):
        self.health=self.original_health
        self.max_health=self.original_health
        self.items={}
        self.status={"psn":0,"aquatised":0}
        self.movement_phase=0
        self.destinations=[]
        self.times=[]
        self.timer=0
        self.velocity=(0,0)
        self.miscs=self.original_miscs
        self.switch_sprite("front")
        self.hurt_timer=0
        self.hurt_surface=None
        return self
    
    def hurt(self, dmg, dmg_type=None):
        global linger_anims
        if dmg != 0:
            if self.health-dmg < 0:
                self.health=0
            else:
                self.health-=dmg
            self.hurt_timer=60
            dmg_colour=(255,0,0)
            if dmg_type == "psn":
                dmg_colour=(60,160,25)
            temp=get_temp_text(large_font,str(dmg),dmg_colour,(self.rect.x,self.rect.y),heart)
            linger_anims.append((temp[0],temp[1],0,60,"inverse up",200))

    def add_item(self,item:Item):
        if item.condition not in self.items:
            self.items[item.condition]=[item]
        else:
            self.items[item.condition].append(item)
        item.placed_on=self

    def remove_item(self,item:Item):
        for key in self.items:
            for subitem in self.items[key]:
                if len(self.items[key]) == 1:
                    del self.items[key]
                    break
                else:
                    if subitem == item:
                        self.items[key].pop(self.items[key].index(subitem))
                    break
            else:
                continue
            break

def get_temp_text(textfont:font.Font,text:str,colour:tuple[int,int,int],loc:Coord,side:Surface=None) -> tuple[Surface,Coord]:
    temp=textfont.render(text,True,colour).convert_alpha()
    if side != None:
        temp_s=Surface((60+temp.get_width()+10,60),SRCALPHA,32).convert_alpha()
        temp_s.blit(side,(0,0))
        temp_s.blit(temp,(70,0))
        return temp_s,(loc[0]+cut_dim[0]/2-temp_s.get_width()/2,loc[1])
    else:
        return temp,(loc[0]+cut_dim[0]/2-temp.get_width()/2,loc[1])

class Item(sprite.Sprite):
    def __init__(self,name:str,cost:int,effect:Callable,sprite:Path,init_pos:Coord,cut_sprite:Path,border:Literal["blue","pink"],dimensions:Size,condition:Literal["end of turn","start of turn","on death","on hurt","on attack","when played"],uses:int,targets:Literal["can be healed","your field","opp field","whole field","all on field","all healable"],id_num:int=0):
        super().__init__()
        #ITEM INFO
        self.name=name
        self.cost=cost
        self.health=0
        self.effect=effect #a function that takes in a value and changes it appropriately
        self.border=border
        self.condition=condition #when the item activates
        self.uses=uses
        self.targets=targets
        self.id_num=id_num
        self.owned_by=None
        self.placed_on=None
        #SPRITE AND COORDS
        if type(sprite) == str:
            self.front_sprite=transform.scale(image.load(sprite),dimensions).convert_alpha()
        else:
            self.front_sprite=sprite
        self.original_sprite=sprite
        if type(sprite) == str:
            self.cut_sprite=transform.scale(image.load(cut_sprite),item_dim).convert()
        else:
            self.cut_sprite=sprite
        self.back_sprite=cardback
        self.current_sprite=self.front_sprite
        self.rect=self.current_sprite.get_rect()
        self.rect.x=init_pos[0]
        self.rect.y=init_pos[1]
        self.display_rect=Rect(large_image_pos[0],large_image_pos[1],card_dim[0]*3,card_dim[1]*3)
        self.internal_coords=list(init_pos)
        self.shade=Surface(card_dim).convert_alpha()
        self.shade.fill((0,0,0,128))
        #MOVEMENT
        self.timer=0
        self.movement_phase=0
        self.destinations=[]
        self.times=[]
        self.velocity=(0,0)

    def __repr__(self):
        temp="None"
        if self.owned_by == player1:
            temp="Player 1"
            if self in player1.hand:
                temp2="hand"
            else:
                temp2="field"
        elif self.owned_by == player2:
            temp="Player 2"
            if self in player2.hand:
                temp2="hand"
            else:
                temp2="field"
        return f"<Item {self.name} in {temp}'s {temp2}>"

    def startmove(self,dests:list[Coord],times:list[int]): #destination as a coord tuple, time in frames
        if self.timer != 0 or (len(self.destinations) > 0 and self.times[-1] == 0):
            self.destinations+=dests
            self.times+=times
        else:
            self.destinations=dests
            self.times=times
            self.movement_phase=0
            self.timer=self.times[self.movement_phase]
            if self.timer != 0:
                self.velocity=((self.destinations[self.movement_phase][0]-self.internal_coords[0])/self.timer, (self.destinations[self.movement_phase][1]-self.internal_coords[1])/self.timer)

    def update(self):
        global move_hovering_over
        if self.owned_by.souls < self.cost or not (False in [entry == None for entry in self.find_targets()]):
            self.playable=False
        else:
            self.playable=True
        if cardback != self.back_sprite:
            self.back_sprite=cardback
        if self.timer!=0:
            self.internal_coords[0]+=self.velocity[0]
            self.internal_coords[1]+=self.velocity[1]
            self.timer-=1
        elif self.timer == 0 and self.movement_phase != len(self.destinations)-1 and self.destinations != [] and self.times[self.movement_phase+1] == 0:
            self.movement_phase+=1
            self.internal_coords[0], self.internal_coords[1]=self.destinations[self.movement_phase]
            self.timer=self.times[self.movement_phase]
        elif self.timer == 0 and self.movement_phase != len(self.destinations)-1 and self.destinations != [] and self.times[0] == 0 and self.movement_phase == 0:
            self.internal_coords[0], self.internal_coords[1]=self.destinations[self.movement_phase]
            self.movement_phase+=1
            self.timer=self.times[self.movement_phase]
            self.velocity=((self.destinations[self.movement_phase][0]-self.internal_coords[0])/self.timer, (self.destinations[self.movement_phase][1]-self.internal_coords[1])/self.timer)
        elif self.timer == 0 and self.movement_phase != len(self.destinations)-1 and self.destinations != []:
            self.movement_phase+=1
            self.timer=self.times[self.movement_phase]
            self.velocity=((self.destinations[self.movement_phase][0]-self.internal_coords[0])/self.timer, (self.destinations[self.movement_phase][1]-self.internal_coords[1])/self.timer)
        else:
            self.destinations=[]
            self.times=[]
            self.movement_phase=0
        if not self.playable and self.owned_by == player1:
            screen.blit(self.shade,(self.rect.x,self.rect.y))
        self.rect.x, self.rect.y=int(self.internal_coords[0]),int(self.internal_coords[1])
        screen.blit(self.current_sprite, (self.rect.x,self.rect.y))

    def switch_sprite(self, final:Literal["front","back","cut"]):
        if final == "front":
            self.current_sprite=self.front_sprite
        elif final == "back":
            self.current_sprite=self.back_sprite
        elif final== "cut":
            self.current_sprite=self.cut_sprite
        self.rect=self.current_sprite.get_rect()

    def find_targets(self) -> list[Card|None]:
        global whole_field
        tempt=[]
        if self.targets == "can be healed":
            for card in player1.field:
                if card != None and card.health != card.max_health:
                    tempt.append(card)
        elif self.targets == "player1 field":
            tempt=player1.field
        elif self.targets == "player2 field":
            tempt=player2.field
        elif self.targets == "whole field":
            tempt=[whole_field]
        elif self.targets == "all on field":
            tempt=player1.field + player2.field
        elif self.targets == "all healable":
            for card in player1.field:
                if card != None and card.health != card.max_health:
                    tempt.append(card)
            for card in player2.field:
                if card != None and card.health != card.max_health:
                    tempt.append(card)
        elif self.targets == "special: goat horn":
            if len([i for i in player2.field if i is not None]) > 1:
                tempt=player2.field
        elif self.targets == "your field":
            if self.owned_by == player1:
                tempt=player1.field
            else:
                tempt=player2.field
        elif self.targets == "opp field":
            if self.owned_by == player1:
                tempt=player2.field
            else:
                tempt=player1.field
        return tempt

class Player():
    def __init__(self,name:str,player_number:int,hand_pos:Coord,field_pos:list[Coord]):
        self.name=name
        self.player_number=player_number
        self.hand:list[Card]=[]
        self.field: list[None|Mob]=[None,None,None]
        self.souls=20
        self.hand_pos=hand_pos
        self.field_pos=field_pos
        self.soul_colour=list(SOUL_COLOUR)
        if player_number == 1:
            self.souls_pos=(field_pos[2][0]+cut_dim[0]+10,window_dim[1]-token_dim[1]-card_dim[1])
            self.deck=deck_p1
        elif player_number == 2:
            self.souls_pos=(field_pos[2][0]+cut_dim[0]+10,50)
            self.deck=deck_p2

    def __repr__(self):
        return f"<Player {str(self.player_number)}>"

    def update(self):
        global abs_subturn
        for i in range(len(self.hand)):
            if self.player_number==2:
                self.hand[i].switch_sprite("back")
            if self.hand[i].destinations == []: # hand_pos x is the same as field_anchor x
                if hand_fill_type == "left":
                    self.hand[i].internal_coords[1], self.hand[i].internal_coords[0]= (self.hand_pos[1],self.hand_pos[0]+card_dim[0]*i)
                elif hand_fill_type == "right":
                    self.hand[i].internal_coords[1], self.hand[i].internal_coords[0]= (self.hand_pos[1],self.hand_pos[0]-card_dim[0]*i)
                elif hand_fill_type == "centre":
                    self.hand[i].internal_coords[1], self.hand[i].internal_coords[0]= (self.hand_pos[1],self.hand_pos[0]+(card_dim[0]*(i))-(len(self.hand)*cut_dim[0])/2+card_dim[0]/2)
            self.hand[i].update()
            #display cards
        for card in self.field:
            if card != None:
                card.update()
                card_pos=self.field_pos[self.field.index(card)]
                draw.rect(screen,(255,0,0),Rect(card_pos[0],hearts_rails[2-self.player_number],cut_dim[0]*card.health/card.max_health,20))
                screen.blit(small_font.render(str(card.health),True,(255,255,255)),(card_pos[0]+5,hearts_rails[2-self.player_number]+1))
                screen.blit(small_font.render(str(card.max_health),True,(255,255,255)),(card_pos[0]-5+cut_dim[0]-round(small_font.size(str(card.max_health))[0]),hearts_rails[2-self.player_number]+1))
                if card.proxy_for != None:
                    draw.line(screen,(255,255,255),(card.rect.centerx,card.rect.y+cut_dim[1]),(card_pos[0]+cut_dim[0]/2,card_pos[1]+cut_dim[1]/2),5)
                temp=0
                for effect in card.status:
                    if card.status[effect] > 0:
                        screen.blit(effect_sprites[effect],(card_pos[0]+25*temp,hearts_rails[2-self.player_number]+copysign(25,(1.5-self.player_number)*-1)))
                        temp+=1
                if card.health <= 0:
                    result=None
                    if "on death" in card.passives:
                        result=card.passives["on death"](origin=card,player=self,loc=(card.rect.x,card.rect.y))
                    if "on death" in card.items:
                        for subitem in card.items["on death"]:
                            result=subitem.effect(origin=card,player=self,item=subitem)
                    if result != False:
                        if card.proxy_for != None:
                            card.proxy_for.proxy=None
                        self.field[self.field.index(card)]=None
                        if self.player_number == 1:
                            abs_subturn -= 1
                if "always" in card.passives:
                    card.passives["always"](origin=card,player=self,loc=(card.rect.x,card.rect.y))
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

    def add_to_field(self,targeting:Literal["self","opp","field"],card:int|Card,fieldpos:int,ignore_cost:bool=False):
        if targeting == "self" or targeting == "field":
            player=self
        elif targeting == "opp":
            if self == player1:
                player=player2
            else:
                player=player1
        else:
            raise ValueError(f"{'\033[91m'}Invalid argument for targeting: {targeting}{'\033[0m'}")
        
        if type(card) == int:
            target=self.hand.pop(card)
        elif type(card) == Mob or type(card) == Item:
            target=card
        else:
            raise TypeError(f"{'\033[91m'}Invalid argument for card: {card}{'\033[0m'}")
        
        if type(target) == Mob:
            player.field[fieldpos]=target
            target.switch_sprite("cut")
            target.startmove([(player.field_pos[fieldpos][0], player.field_pos[fieldpos][1]+copysign(cut_dim[1],1.5-player.player_number))],[0])
            target.startmove([player.field_pos[fieldpos]],[15])
            if not ignore_cost:
                self.souls -= target.cost
        else:
            if target.condition != "when played":
                temp=copy.copy([target.rect.x, target.rect.y])
                player.field[fieldpos].add_item(target)
                target.placed_on=player.field[fieldpos]
                target.switch_sprite("cut")
                target.internal_coords=temp
                target.startmove([(player.field[fieldpos].rect.x+cut_dim[0]*2/3, player.field[fieldpos].rect.y+item_dim[1]*denest(player.field[fieldpos].items).index(target))],[30])
                if not ignore_cost:
                    self.souls -= target.cost
            else:
                if targeting != "field":
                    target.placed_on=player.field[fieldpos]
                    target.effect(target=player.field[fieldpos], origin=target, player=player, item=target)
                else:
                    target.effect(target=whole_field,origin=target,player=player1,item=target)

    def reset(self):
        self.hand=[]
        self.field=[None, None, None]
        self.souls=20

class ClickableText():
    def __init__(self,font:font.Font,text:str,colour:tuple[int,int,int],position:Coord):
        self.text=font.render(text,True,colour)
        self.raw_text=text
        self.textrect=self.text.get_rect()
        self.position=position
        self.textrect.x=position[0]
        self.textrect.y=position[1]

class Ability():
    def __init__(self,cost:int,effect:Callable,targets:str,name:str=None):
        self.cost=cost
        self.effect=effect
        self.targets=targets
        if name == None:
            self.name=effect.__name__
        else:
            self.name=name

    def __repr__(self):
        return f"<Ability {self.name}>"

    def find_targets(self, selected):
        global whole_field
        tempt=[]
        if self.targets == "can be healed":
            for card in player1.field:
                if card != None and card.health != card.max_health:
                    tempt.append(card)
        elif self.targets == "player1 field":
            tempt=player1.field
        elif self.targets == "player2 field":
            tempt=player2.field
        elif self.targets == "whole field":
            tempt=[whole_field]
        elif self.targets == "all on field":
            tempt=player1.field + player2.field
        elif self.targets == "all healable":
            for card in player1.field:
                if card != None and card.health != card.max_health:
                    tempt.append(card)
            for card in player2.field:
                if card != None and card.health != card.max_health:
                    tempt.append(card)
        elif self.targets == "can proxy":
            tempt=[mob for mob in player1.field if (mob != None and mob.proxy == None and mob.proxy_for == None and mob != selected)]
        return tempt
    
    def use(self,**kwargs):
        stop=False
        if kwargs["player"].player_number == 1:
            opp=player2
        else:
            opp=player1
        match=opp.field[kwargs["player"].field.index(kwargs["origin"])]
        if "on action" in kwargs["origin"].items:
            maybe=tuple(kwargs["origin"].items["on action"])
            for subitem in maybe:
                stop=subitem.effect(origin=kwargs["origin"],target=kwargs["target"],player=kwargs["player"],item=subitem)
        if stop == True or (match != None and match.name == "Frog"): #egg rain and tongue snare
            result=None
        else:
            result=self.effect(**kwargs)
            if (type(result) == bool and result == True) or (type(result) == tuple and result[0] == True):
                temp=get_temp_text(large_font,self.name,(250,100,250),kwargs["loc"])
                linger_anims.append((temp[0],temp[1],0,60,"inverse down",200))
            if type(result) == tuple:
                result=result[1]
        return result

class Tile(): #a simplified container for card data
    def __init__(self,name:str,full_sprite:Surface,cut_sprite:Surface,kind:Literal["Mob"]|Literal["Item"],border:Literal["blue"]|Literal["pink"],position:Coord):
        self.name=name
        self.full_sprite=full_sprite
        self.cut_sprite=cut_sprite
        self.kind=kind
        self.border=border
        self.position=position
        self.rect=cut_sprite.get_rect(x=position[0],y=position[1])

    def __repr__(self):
        return f"<Tile for {self.name}>"

    def display(self):
        screen.blit(self.cut_sprite,(self.rect.x,self.rect.y))

    def nearcopy(self,**kwargs) -> Tile:
        new_name=self.name
        if "name" in kwargs:
            new_name=kwargs["name"]
        new_full=self.full_sprite
        if "full_sprite" in kwargs:
            new_full=kwargs["full_sprite"]
        new_cut=self.cut_sprite
        if "cut_sprite" in kwargs:
            new_cut=kwargs["cut_sprite"]
        new_kind=self.kind
        if "kind" in kwargs:
            new_kind=kwargs["kind"]
        new_border=self.border
        if "border" in kwargs:
            new_border=kwargs["border"]
        new_pos=self.position
        if "position" in kwargs:
            new_pos=kwargs["position"]
        return Tile(new_name,new_full,new_cut,new_kind,new_border,new_pos)

class DeckPreset(): #this gets confusing fast so I'll be leaving some comments
    def __init__(self,name:str,number:int,colour:tuple[int,int,int],mobs:dict[str,int],items:dict[str,int]):
        self.name=name
        self.number=number
        self.colour=colour
        self.original_mobs:dict[str,int]=mobs #strings are names of the variables that represent mobs, supposed to be evaled
        self.original_items:dict[str,int]=items
        self.item_offset=0
        self.set_rects()
        self.title_bg_rect=Rect(10,10,window_dim[0]-20,88)
        self.text=large_font.render(name,True,contrast(colour))
        self.unpack(mobs,items)
        self.info_text=None
        self.plus1_text=None
        self.minus1_text=None
        self.pink_mob=False
        self.pink_item=False

    def __repr__(self):
        return f"<Deck Preset {self.name}>"
            
    def to_dict(self):
        return [self.name,{"number":self.number,"colour":self.colour,"mobs":self.original_mobs,"items":self.original_items}]
    
    def display(self):
        global selected_deck
        global editing_deck_title
        global cards_sidebar
        if selected_deck == None:
            draw.rect(screen,(0,0,0),self.outer_rect)
            draw.rect(screen,self.colour,self.inner_rect)
            screen.blit(self.text,(self.inner_rect.x+10,self.inner_rect.y+10))
            if deleting_deck == True:
                draw.rect(screen,(255,0,0),Rect(window_dim[0]-90,113+20+(128*self.number),60,60))
                screen.blit(self.delete.text,self.delete.position)
            if chosen_deck == self:
                draw.rect(screen,(0,255,0),Rect(window_dim[0]-170,113+20+(128*self.number),60,60))
        elif selected_deck == self:
            draw.rect(screen,self.colour,self.title_bg_rect)
            screen.blit(self.text,(window_dim[0]/2-self.text.get_width()/2,15))
            screen.blit(deck_mobs_text,(10,110))
            screen.blit(mjgs.render(f"{sum(list(self.original_mobs.values()))}/8",True,(0,0,0)),(200,110))
            screen.blit(deck_items_text,(10,380))
            screen.blit(mjgs.render(f"{sum(list(self.original_items.values()))}/10",True,(0,0,0)),(250,380))
            for mob in list(self.mobs.keys()):
                if selected == mob:
                    draw.rect(screen,(255,255,255),Rect(mob.rect.x-5,mob.rect.y-5,cut_dim[0]+10,cut_dim[1]+10))
                screen.blit(mob.cut_sprite,mob.rect)
                screen.blit(mjgs.render(f"x{self.mobs[mob]}",True,(0,0,0)),(mob.rect.x+(cut_dim[0]/2-mjgs.size(f"x{self.mobs[mob]}")[0]/2),mob.rect.y+cut_dim[1]+10))
            for i in range(len(self.items)):
                item=list(self.items.keys())[i]
                if selected == item:
                    draw.rect(screen,(255,255,255),Rect(item.rect.x-5,item.rect.y-5,cut_dim[0]+10,cut_dim[1]+10))
                screen.blit(item.cut_sprite,(item.rect.x,item.rect.y))
                screen.blit(mjgs.render(f"x{self.items[item]}",True,(0,0,0)),(item.rect.x+(cut_dim[0]/2-mjgs.size(f"x{self.items[item]}")[0]/2),item.rect.y+cut_dim[1]+10))
            if self.item_offset > 0:
                draw.circle(screen,M_BLUE,(items_left[1].x+20,items_left[1].y+20),25)
                screen.blit(items_left[0],items_left[1])
            if len(list(self.items.keys())) > 8 and not 8+self.item_offset == len(list(self.items.keys())):
                draw.circle(screen,M_BLUE,(items_right[1].x+20,items_right[1].y+20),25)
                screen.blit(items_right[0],items_right[1])
            if selected != None:
                draw.rect(screen,(15,180,220),Rect(selected.rect.x+10,selected.rect.y+cut_dim[1]/2+5,cut_dim[0]-20,70))
                if (selected.rect.y < 380 and sum(list(self.original_mobs.values())) > 7) or (selected.rect.y > 380 and sum(list(self.original_items.values())) > 9) or not ((selected.border == "pink" and self.pink_mob == False) or selected.border == "blue"):
                    draw.circle(screen,(128,128,128),(selected.rect.x+5+40,selected.rect.y+45),35)
                else:
                    draw.circle(screen,(0,255,0),(selected.rect.x+5+40,selected.rect.y+45),35)
                draw.circle(screen,(255,0,0),(selected.rect.x+5+120,selected.rect.y+45),35)
                screen.blit(self.info_text.text,self.info_text.position)
                screen.blit(self.plus1_text.text,self.plus1_text.position)
                screen.blit(self.minus1_text.text,self.minus1_text.position)
            if selected_large != None:
                if cards_sidebar:
                    screen.blit(selected_large,(10,100))
                else:
                    screen.blit(selected_large,(window_dim[0]/2-card_dim[0]*1.5,100))
            screen.blit(colour_wheel,(colour_wheel_rect.x,colour_wheel_rect.y))
            if editing_deck_title == True and tm.time()%1>0.5:
                draw.rect(screen,contrast(self.colour),Rect(self.text.get_size()[0]/2+window_dim[0]/2,20,5,70))

    def set_renders(self,card_rect:Rect|None):
        if card_rect == None:
            self.info_text=None
            self.plus1_text=None
            self.minus1_text=None
        else:
            self.info_text=ClickableText(mjgs,"Info",(255,255,255),(card_rect.x+45,card_rect.y+cut_dim[1]/2+20))
            self.plus1_text=ClickableText(mjgs,"+1",(255,255,255),(selected.rect.x+5+17,selected.rect.y+25))
            self.minus1_text=ClickableText(mjgs,"-1",(255,255,255),(selected.rect.x+5+97,selected.rect.y+25))

    def set_rects(self):
        self.outer_rect=Rect(0,100+(128*self.number),window_dim[0],128) #these two hold the position of the deck in the preset screen
        self.inner_rect=Rect(20,100+20+(128*self.number),window_dim[0]-40,88)
        self.delete=ClickableText(large_font,"x",(0,0,0),(window_dim[0]-80,100+20+(128*self.number)))

    def deck_change_clicks(self,pos:Coord) -> bool:
        global selected_large
        temp=False
        temp2=False
        if self.info_text.textrect.collidepoint(pos):
            if selected in list(self.mobs.keys()):
                selected_large=selected.full_sprite
                temp=True
            elif selected in list(self.items.keys()):
                selected_large=selected.full_sprite
                temp=True
        elif self.plus1_text.textrect.collidepoint(pos):
            if selected in self.mobs and sum(list(self.original_mobs.values())) < 8 and ((selected.border == "pink" and self.pink_mob == False) or selected.border == "blue"):
                self.original_mobs[list(self.original_mobs.keys())[list(self.mobs.keys()).index(selected)]]+=1
                if selected.border == "pink":
                    self.pink_mob = True
                temp=True
            elif selected in self.items and sum(list(self.original_items.values())) < 10 and ((selected.border == "pink" and self.pink_mob == False) or selected.border == "blue"):
                self.original_items[list(self.original_items.keys())[list(self.items.keys()).index(selected)]]+=1
                if selected.border == "pink":
                    self.pink_item = True
                temp=True
        elif self.minus1_text.textrect.collidepoint(pos):
            if selected in self.mobs:
                self.original_mobs[list(self.original_mobs.keys())[list(self.mobs.keys()).index(selected)]]-=1
                if self.original_mobs[list(self.original_mobs.keys())[list(self.mobs.keys()).index(selected)]] == 0:
                    self.original_mobs.pop(list(self.original_mobs.keys())[list(self.mobs.keys()).index(selected)])
                    if selected.border == "pink":
                        self.pink_mob = False
                    temp2=True
                temp=True
            elif selected in self.items:
                self.original_items[list(self.original_items.keys())[list(self.items.keys()).index(selected)]]-=1
                if self.original_items[list(self.original_items.keys())[list(self.items.keys()).index(selected)]] == 0:
                    self.original_items.pop(list(self.original_items.keys())[list(self.items.keys()).index(selected)])
                    if selected.border == "pink":
                        self.pink_item = False
                    temp2=True
                temp=True
        if temp:
            self.unpack(self.original_mobs,self.original_items,"whitelist",["items","mobs","pinks"])
        if temp2:
            self.unpack(self.original_mobs,self.original_items)
        return temp
    
    def deck_other_clicks(self,pos:Coord):
        global chosen_deck
        global decklist_p1
        global menu_deck_selected_text
        if items_left[1].collidepoint(pos) and self.item_offset > 0:
            self.item_offset -= 1
            for item in list(self.items.keys()):
                item.rect.x += (cut_dim[0]+20)
        elif items_right[1].collidepoint(pos) and sum(list(self.items.values())) > 8 and not 8+self.item_offset == sum(list(self.items.values())):
            self.item_offset += 1
            for item in list(self.items.keys()):
                item.rect.x -= (cut_dim[0]+20)
        elif select_deck_text.textrect.collidepoint(pos):
            if self.usable == True:
                chosen_deck=self
                decklist_p1={"mobs":{eval(mob):self.original_mobs[mob] for mob in self.original_mobs},"items":{eval(item):self.original_items[item] for item in self.original_items}}
                menu_deck_selected_text=mjgs.render(chosen_deck.name,True,contrast(chosen_deck.colour))
    
    def deck_delete_clicks(self,pos:Coord):
        global deleting_deck
        if deleting_deck == True:
            temp=False
            if self.delete.textrect.collidepoint(pos):
                for deck in deck_presets:
                    if deck.number > self.number:
                        deck.number-=1
                        deck.set_rects()
                deck_presets.pop(self.number)
                deleting_deck=False
                temp=True
            return temp
        
    def edit_title(self,e):
        global editing_deck_title
        global menu_deck_selected_text
        if e.key == K_BACKSPACE:
            self.name = self.name[:-1]
        elif e.key == K_RETURN or e.key == K_ESCAPE:
            editing_deck_title=False
        elif e.key != K_LESS and e.key != K_GREATER:
            self.name += e.unicode
        self.text=large_font.render(self.name,True,contrast(self.colour))
        menu_deck_selected_text=mjgs.render(self.name,True,contrast(self.colour))
    
    def unpack(self,mobs:dict[str,int],items:dict[str,int],targettype:Literal["blacklist"]|Literal["whitelist"]="all",targets:list=[]):
        target_list=["mobs","items","pinks"]
        if targettype == "blacklist":
            target_list=[var for var in target_list if var not in targets]
        elif targettype == "whitelist":
            target_list=[var for var in target_list if var in targets]
        if "mobs" in target_list:
            self.mobs:dict[Tile,int]={d_tiles[x].nearcopy(position=(deck_cards_pos[list(mobs.keys()).index(x)],160)):mobs[x] for x in list(mobs.keys())} #strings are those that represent the card info that can be evaled into card objects, ints are amounts
        if "items" in target_list:
            self.items:dict[Tile,int]={d_tiles[x].nearcopy(position=(deck_cards_pos[list(items.keys()).index(x)]-(cut_dim[0]+20)*self.item_offset,430)):items[x] for x in list(items.keys())}
        if "pinks" in target_list:
            self.pink_mob=False
            self.pink_item=False
            for mob in self.mobs:
                if mob.border == "pink":
                    self.pink_mob=True
            for item in self.items:
                if item.border == "pink":
                    self.pink_item=True
        if sum(self.original_items.values()) == 10 and sum(self.original_mobs.values()) == 8:
            self.usable = True
        else:
            self.usable=False

class BGTile(): #a container for background changing information
    def __init__(self,img:Surface,path:Path,name:str,pos:Coord):
        self.img=img
        self.path=path
        self.name=name
        self.text=mjgs.render(name,True,(0,0,0))
        self.pos=pos
        self.rect=self.img.get_rect(x=pos[0],y=pos[1])
        self.textpos=(pos[0]+(self.rect.width/2-self.text.get_width()/2),pos[1]+self.rect.height+20)

    def __repr__(self):
        return f"Background Tile for {self.name}"

    def display(self):
        if chosen_card_bg == self.name:
            draw.rect(screen,ORANGE,Rect(self.pos[0]-10,self.pos[1]-10,self.rect.width+20,self.rect.height+20))
        screen.blit(self.img,self.pos)
        screen.blit(self.text,self.textpos)

class LayoutTile(): # a container for game layout information
    def __init__(self,name:str,text:Surface,field_anchor:Coord,x_spacing:int,y_spacing:int,large_img_pos:Coord,dck_plc_pos:Coord,display_pos:Coord,lrg_hideable:bool,hand_fill:Literal["left"]|Literal["right"]|Literal["centre"],sbt_indic_pos:Coord,hand_anchor:Coord=None,img:Surface=Surface((0,0))):
        self.name=name
        self.text=text
        self.field_anchor=field_anchor
        if hand_anchor == None:
            self.hand_anchor=self.field_anchor
        else:
            self.hand_anchor=hand_anchor
        self.x_spacing=x_spacing
        self.y_spacing=y_spacing
        self.large_image_pos=large_img_pos
        self.deck_plc_pos=dck_plc_pos
        self.large_hideable=lrg_hideable
        self.img=img
        self.display_pos=display_pos
        self.hand_fill_type=hand_fill
        self.subturn_indic_pos=sbt_indic_pos
        self.display_surf=Surface((self.text.get_rect().width+30+self.img.get_rect().width,max(self.text.get_rect().height,self.img.get_rect().height)),SRCALPHA,32).convert_alpha()
        self.display_surf.blit(self.text,(0,self.img.get_rect().height/2-self.text.get_height()/2))
        self.display_surf.blit(self.img,(self.text.get_rect().width+30,0))
        self.rect=self.display_surf.get_rect(left=self.display_pos[0],top=self.display_pos[1])

    def __repr__(self):
        return f"Layout Container for {self.name}"

    def display(self):
        screen.blit(self.display_surf,self.rect)
        if chosen_layout_name == self.name:
            draw.rect(screen,ORANGE,Rect(self.rect.x-10,self.rect.y-10,self.rect.width+20,self.rect.height+20),10)

def excepthook(type, value, traceback):
    print(f"Error: {type.__name__}\nReason: {value}\nTraceback :\n{str(t.format_tb(traceback))}")
    name="crashes\\crash_log_"+str(tm.time())+".txt"
    temp_tb=t.format_tb(traceback)
    crashlog=open(name,"wt")
    crashlog.write("If you are seeing this, please contact the creator with this file here:\n24149007@imail.sunway.edu.my\n\n")
    crashlog.write(f"Game ID: {game_id}\nTime: {tm.asctime()}\nError: {type.__name__}\nReason: {value}\nTraceback :")
    for i in range(len(temp_tb)):
        crashlog.write(f"{temp_tb[i]}\n")
    crashlog.close()
    os.startfile(name)

def start_of_turn():
    for card in player1.field:
        if card != None and "start of turn" in card.passives:
            card.passives["start of turn"](loc=(card.rect.x,card.rect.y))
        if card != None and "start of turn" in card.items:
            for subitem in card.items["start of turn"]:
                subitem.effect(item=subitem,origin=card,player=player1)
    for card in player2.field:
        if card != None and "start of turn" in card.passives:
            card.passives["start of turn"](loc=(card.rect.x,card.rect.y))
        if card != None and "start of turn" in card.items:
            for subitem in card.items["start of turn"]:
                subitem.effect(item=subitem,origin=card,player=player2)

def deckbuilder(list_to_use:dict[Card,int]) -> list[Card]:
    here_deck=[]
    for card in list_to_use:
        for i in range(list_to_use[card]):
            actual_card=eval(card)
            here_deck.append(actual_card)
    shuffle(here_deck)
    return here_deck

def draw_card(player:Player,draw_from:list[Card],amount:int=1,override:Card=None) -> list[Card]|Card: # type: ignore
    global hand_size_limit
    if (draw_from == [] and player == player1) or (player == player2 and override == None and not markers["do not connect"]):
        return
    card_list=[]
    for i in range(amount):
        if len(player.hand) != hand_size_limit:
            if override == None:
                card=draw_from.pop()
            else:
                card=override
            player.hand.append(card)
            card_list.append(card)
            card.internal_coords=list(deck_plc_pos)
            if hand_fill_type == "left":
                card.startmove([(player.hand_pos[0]+card_dim[0]*(len(player.hand)-1),player.hand_pos[1])],[30])
            elif hand_fill_type == "right":
                card.startmove([(player.hand_pos[0]-card_dim[0]*(len(player.hand)-1),player.hand_pos[1])],[30])
            elif hand_fill_type == "centre":
                card.startmove([(player.hand_pos[0]+(card_dim[0]*(len(player.hand)-1))-(len(player.hand)*cut_dim[0])/2,player.hand_pos[1])],[30])
            card.owned_by=player
        if player == player1 and not markers["do not connect"]:
            write_buffer.append("d"+str(card.id_num)+"END")
    if len(card_list) == 1:
        return card_list[0]
    else:
        return card_list

def denest(container:dict|list) -> list:
    result=[]
    if type(container) == dict:
        keys=list(container.keys())
    elif type(container) == list:
        keys=[i for i in range(len(container))]
    for key in keys:
        if type(container[key]) != list and type(container[key]) != dict:
            result.append(container[key])
        elif type(container[key]) == list:
            for item in container[key]:
                result.append(item)
        elif type(container[key]) == dict:
            result.append(denest(container[key]))
        else:
            result.append(None)
    return result

def len_items(items:dict) -> int:
    return len(denest(items))

def contrast(colour:tuple[int,int,int]):
    brightness=0.299*colour[0] + 0.587*colour[1] + 0.114*colour[2]
    if brightness <= 0.5:
        return (255,255,255)
    else:
        return (0,0,0)

def unpack():
    global deck_presets
    if infojson != {}:
        deck_presets=[]
        for deck_name in infojson:
            if deck_name[0] != "<":
                deck_presets.append(DeckPreset(deck_name,infojson[deck_name]["number"],infojson[deck_name]["colour"],infojson[deck_name]["mobs"],infojson[deck_name]["items"]))

def execute(instr:bytes|None) -> tuple[bool,bool]: #executes moves on behalf of player2 according to a instruction string
    global markers
    global state
    global setup
    global player2name
    markers["disconnecting"]=False
    progress_turn=False
    if instr != None and instr.decode() != "":
        instr:str=instr.decode()
    else:
        return False, False
    if instr[0] == "n": #receiving name
        player2name=instr[1:]
        return_val=False
    elif instr[0] == "c": #opponent conceded
        state="win"
        setup=False
        markers["concede"]="opp"
        return_val=False
    elif instr[0] == "m": #attack used
        attacker=player2.field[int(instr[1])]
        attacked=player1.field[int(instr[3])]
        counter=attacker.moveset[int(instr[2])](origin=attacker,target=attacked,player=player2,noattack=False)
        attacker.startmove([(attacked.rect.x,attacked.rect.y),(attacker.rect.x,attacker.rect.y)],[10,10])
        if len(attacked.moveset) > 0:
            other_counter=attacked.moveset[0](origin=attacked,target=attacker,player=player1,noattack=True)
        else:
            counter=False
            other_counter=not counter
        if (counter == True or counter == other_counter) and len(attacked.moveset) > 0:
            attacked.moveset[0](origin=attacked,target=attacker,player=player1,noattack=False)
        progress_turn=True
        return_val=False
    elif instr[0] == "i": #placed item
        if instr[2] == "3":
            player2.add_to_field("field",player2.hand[int(instr[1])],None)
        elif instr[3] == "2":
            player2.add_to_field("self",int(instr[1]),int(instr[2]))
        elif instr[3] == "1":
            player1.add_to_field("self",player2.hand[int(instr[1])],int(instr[2]),True)
        progress_turn=True
        return_val=False
    elif instr[0] == "a": #ability used
        if instr[3] == "3":
            player2.field[int(instr[1])].abilities[int(instr[2])].use(origin=player2.field[int(instr[1])],target=whole_field,player=player2,loc=(player2.field[int(instr[1])].rect.x,player2.field[int(instr[1])].rect.y))
        elif instr[4] == "2":
            player2.field[int(instr[1])].abilities[int(instr[2])].use(origin=player2.field[int(instr[1])],target=player2.field[int(instr[3])],player=player2,loc=(player2.field[int(instr[1])].rect.x,player2.field[int(instr[1])].rect.y))
        elif instr[4] == "1":
            player2.field[int(instr[1])].abilities[int(instr[2])].use(origin=player2.field[int(instr[1])],target=player1.field[int(instr[3])],player=player2,loc=(player2.field[int(instr[1])].rect.x,player2.field[int(instr[1])].rect.y))
        progress_turn=True
        return_val=False
    elif instr[0] == "d": #drew card
        draw_card(player2,[],1,override=eval(all_ids[int(instr[1:])]))
        return_val=markers["await p2"]
    elif instr[0] == "p": #placed mob
        player2.add_to_field("self",int(instr[1]),int(instr[2]))
        progress_turn=True
        return_val=False
    elif instr[0] == "g" or instr[0] == "x": #game continuing or no available moves, just proceed
        if not markers["disconnecting"] and markers["await p2"]:
            markers["disconnecting"] == True
        elif not markers["await p2"]:
            markers["disconnecting"] == False
        if instr[0] == "g":
            return_val=markers["await p2"]
        else:
            return_val=False
        if setup and markers["await p2"]:
            return_val=markers["await p2"]
            markers["disconnecting"]=True
    elif instr[0] == "t":
        state == "lose"
        setup=False
        markers["concede"]="you"
        markers["you timeout"]=True
        print(f"{'\033[93m'}Conceding by timeout{'\033[0m'}")
        return_val=True
    else:
        raise RuntimeError(f"Invalid instructions received: {instr}")
    if setup:
        progress_turn=False
    return return_val, progress_turn
    #print(instr)

def p2_move(hand:list[Card],field:list[Mob|None],souls:int) -> bytes: #returns an encoded string to be passed to execute()
    hand=copy.copy(hand)
    field=copy.copy(field)
    available_cards=hand+field
    while True:
        result:str=''
        selected_card:Card=choice(available_cards)
        if type(selected_card) == Mob:
            if selected_card in field:
                selected_move=choice(selected_card.move_positions)
                if selected_card.move_positions.index(selected_move) < len(selected_card.moveset):
                    selected_move=selected_card.moveset[selected_card.move_positions.index(selected_move)]
                else:
                    selected_move=selected_card.abilities[selected_card.move_positions.index(selected_move)-len(selected_card.moveset)]
                if type(selected_move) == Ability: 
                    if selected_move.cost <= souls:
                        result += "a"
                        result += str(field.index(selected_card))
                        result += str(selected_card.abilities.index(selected_move))
                        target=choice(selected_move.find_targets())
                        if target in player1.field:
                            result += player1.field.index(target)
                            result += "1"
                        elif target in player2.field:
                             result += player2.field.index(target)
                             result += "2"
                        else:
                            result += "3"
                        break
                else:
                    result += "m"
                    result += str(field.index(selected_card))
                    result += str(selected_card.moveset.index(selected_move))
                    result += str(choice([i for i in range(len(player1.field)) if player1.field[i] != None]))
                    break
            elif selected_card in hand:
                result += "p"
                open_field_slots=[i for i in range(len(field)) if field[i] == None]
                if open_field_slots != [] and selected_card.cost <= souls:
                    result += str(hand.index(selected_card))
                    result += str(choice(open_field_slots))
                    break #mob placed, choose from empty slots
        elif type(selected_card) == Item:
            if selected_card.cost <= souls:
                result += "i"
                result += str(hand.index(selected_card))
                target=choice(selected_card.find_targets())
                if target in player1.field:
                    result += str(player1.field.index(target))
                    result += "1"
                elif target in player2.field:
                        result += str(player2.field.index(target))
                        result += "2"
                else:
                    result += "3"
                break #item used (split by targeting)
        available_cards.remove(selected_card)
        if available_cards == []:
            result="x"
            break
    return result.encode()

def retry_del(func,path,exc):
    print(f"Failed to delete {path}. Retrying...")
    os.chmod(path, stat.S_IWRITE)
    func(path)
    print(f"Successfully removed: {path}")

def uninstall(arg):
    for file in os.listdir(arg):
        if file != os.path.basename(__file__):
            print(f"Removing: {os.path.join(arg,file)}")
            rmtree(os.path.join(arg,file),onexc=retry_del)
    rmtree(__path__,onexc=retry_del)
    rmtree(arg,onexc=retry_del)

def atk_check(func) -> bool: #decorator that applies to all attacks
    def atk_wrapper(**kwargs):
        global markers
        stop=False
        if kwargs["noattack"] == False:
            result:list[bool,int,list[Card]]=list(func(**kwargs))
            if markers["forage"] > 1: #forage
                markers["forage"] -= 1
            elif markers["forage"] == 1:
                result[1] += 1
                markers["forage"]=False
            if len(result) == 2:
                result.append([kwargs["target"]])
            if "on action" in kwargs["origin"].items:
                maybe=tuple(kwargs["origin"].items["on action"])
                for subitem in maybe:
                    stop=subitem.effect(origin=kwargs["origin"],target=kwargs["target"],player=kwargs["player"],item=subitem)
            for card in result[2]:
                if stop == True:
                    break
                if "on attack" in kwargs["origin"].items:
                    maybe=tuple(kwargs["origin"].items["on attack"])
                    for subitem in maybe:
                        result=subitem.effect(origin=kwargs["origin"],target=card,player=kwargs["player"],original=result,item=subitem)
                        if len(result) == 4:
                            break
                if card.proxy != None:
                    card=card.proxy
                card.hurt(result[1])
                if kwargs["origin"] in player2.field: #quick strike
                    for mob in [mob for mob in player1.field if (mob != None and mob.name == "Horse")]:
                        mob.passives["special: quick strike"](origin=kwargs["origin"],target=kwargs["target"],player=kwargs["player"],striker=mob,loc=(mob.rect.x,mob.rect.y))
                if "on hurt" in card.passives and result[1] != 0:
                    card.passives["on hurt"](origin=kwargs["origin"],target=card,player=kwargs["player"],damage=result[1],loc=(card.rect.x,card.rect.y))
                if "on hurt" in card.items and result[1] != 0:
                    for subitem in card.items["on hurt"]:
                        subitem.effect(origin=kwargs["origin"],target=card,player=kwargs["player"],original=result[1],item=subitem)
            return result[0]
        else:
            return func(origin=kwargs["origin"],target=kwargs["target"],player=kwargs["player"],noattack=True)[0]
    return atk_wrapper

def psv_check(func): #decorator that applies to all passives
    def psv_wrapper(**kwargs):
        opp=None
        if kwargs["origin"] in player1.field:
            opp=player2
        else:
            opp=player1
        try:
            match=opp.field[kwargs["player"].field.index(kwargs["origin"])]
        except:
            match=preset_dummy
        if match != None and match.name == "Frog": #tongue snare
            result=None
        else:
            result=func(**kwargs)
            if (type(result) == bool and result == True) or (type(result) == tuple and result[0] == True):
                temp=get_temp_text(large_font," ".join(func.__name__.split("_")).capitalize(),(255,255,255),kwargs["loc"])
                linger_anims.append((temp[0],temp[1],0,60,"inverse down",200))
            if type(result) == tuple:
                result=result[1]
            #print(f"{func.__name__} used.")
        return result
    return psv_wrapper

def itm_check(func): #decorator that applies to all items
    def itm_wrapper(**kwargs):
        result=None
        targets:list=func(origin=kwargs["origin"],target=kwargs["target"],player=kwargs["player"],only_targeting=True)
        if "original" not in kwargs:
            kwargs["original"]=0
        for card in targets:
            if (card != None and card.name != "Sunken") or (card == None and kwargs["origin"].condition == "when played"): #porous body
                if card == None:
                    result=func(**kwargs)
                else:
                    result=func(origin=kwargs["origin"],target=card,player=kwargs["player"],original=kwargs["original"])
                kwargs["item"].uses-=1
        if kwargs["item"].uses <= 0 and (targets == [None] or kwargs["item"].condition == "when played"):
            kwargs["item"].owned_by.hand.pop(kwargs["item"].owned_by.hand.index(kwargs["item"]))
        elif kwargs["item"].uses <= 0 and targets != [None]:
            kwargs["item"].placed_on.remove_item(kwargs["item"])
        return result
    return itm_wrapper

def run_once(func): #decorator that ensures functions run only once
    def ro_wrapper(**kwargs):
        if not ro_wrapper.has_run:
            ro_wrapper.has_run=True
            return func(**kwargs)
    ro_wrapper.has_run=False
    return ro_wrapper

@itm_check
def nofunction_item(**kwargs):
    pass

#region gameplay functions
@atk_check
def bite(**kwargs:Attack_params) -> tuple[Literal[True],Literal[2]]: #attack
    dmg=0
    if kwargs["noattack"] == False:
        dmg=2
    return True, dmg

@itm_check
def bread_heal(**kwargs): #item
    if "only_targeting" not in kwargs:
        kwargs["target"].heal(2)
    else:
        return [kwargs["target"]]

@itm_check
def cake_heal(**kwargs): #item
    if "only_targeting" not in kwargs:
        kwargs["target"].heal(1)
    else:
        return [mob for mob in player1.field if mob != None]

@psv_check
def child_support_avoider(**kwargs) -> Literal[True]|None: #passive: always
    if kwargs["player"].player_number == 1:
        opp=player2
    else:
        opp=player1
    if len([mob for mob in opp.field if mob != None]) == 1 and setup == False:
        kwargs["origin"].health=0
        return True
    
@atk_check
def drown(**kwargs:Attack_params) -> tuple[Literal[True],int]: #attack
    dmg=0
    if kwargs["noattack"] == False:
        if kwargs["target"].mob_class == "aquatic" or kwargs["target"].status["aquatised"] > 0:
            dmg=3
        else:
            dmg=2
    kwargs["target"].status["aquatised"] = 2
    return True, dmg

@itm_check
def egg_rain_activate(**kwargs) -> tuple[bool,int,list,str]:
    if "only_targeting" not in kwargs:
        return True
    else:
        return [kwargs["origin"]]

@psv_check
@run_once
def elders_curse(**kwargs) -> Literal[True]: #passive: end of turn
    global selected
    global selected_move
    global attack_progressing
    global move_hovering_over
    global targets
    global hide_large
    if kwargs["player"] == player1 and kwargs["origin"] in player1.field:
        selected=kwargs["origin"]
        hide_large=False
        selected_move=kwargs["origin"].moveset[0]
        attack_progressing=True
        move_hovering_over=(kwargs["origin"].move_positions[0],kwargs["origin"].moveset[0])
        targets=player2.field
        return True

@atk_check
def eye_laser(**kwargs:Attack_params) -> tuple[Literal[False],int]: #attack
    dmg=0
    if kwargs["noattack"] == False:
        if kwargs["player"].player_number == 1:
            opp=player2
        else:
            opp=player1
        dmg=1
        if kwargs["player"].field.index(kwargs["origin"])-opp.field.index(kwargs["target"]) != 0:
            dmg+=1
    return False, dmg

@psv_check
def forage(**kwargs) -> Literal[True]: #passive: on this turn
    global markers
    markers["forage"]=3
    return True

@itm_check
def goat_horn_bounce(**kwargs): #item
    if "only_targeting" not in kwargs:
        player2.field[player2.field.index(kwargs["target"])]=None
        player2.hand.append(kwargs["target"].reset())
        kwargs["target"].switch_sprite("back")
    else:
        return [kwargs["target"]]

@psv_check
def infinity(**kwargs) -> Literal[True]: #passive: on hurt
    kwargs["target"].health+=kwargs["damage"]-1
    return True

@atk_check
def knife_thing(**kwargs:Attack_params) -> tuple[Literal[True],int]:
    dmg=0
    if kwargs["noattack"] == False:
        if kwargs["target"].name == "Satoru Gojo":
            dmg=kwargs["target"].health-1
        else:
            dmg=kwargs["target"].health
    return True, dmg

@itm_check
def loot_chest_draw(**kwargs): #item
    if "only_targeting" not in kwargs:
        draw_card(kwargs["player"],kwargs["player"].deck["items"],2)
    else:
        return [None]

@itm_check
def milk_cleanse(**kwargs): #item
    if "only_targeting" not in kwargs:
        kwargs["target"].items={}
    else:
        return [kwargs["target"]]

#abl_check
def milk_share(**kwargs) -> bool: #ability
    result=False
    if kwargs["player"].souls >= 1:
        result=True
        for card in kwargs["player"].field:
            if card != None and card != kwargs["origin"]:
                card.heal(1)
        kwargs["player"].souls -= 1
    return result

#abl_check
def monkey(**kwargs) -> Literal[True]:
    global markers
    markers["monkey"]=60
    return True

@psv_check
def mystery_egg(**kwargs) -> Literal[True]: #passive: on this turn
    draw_card(kwargs["player"],kwargs["player"].deck["items"])
    return True

#abl_check
def nah_id_win(**kwargs) -> Literal[True]: #ability
    if kwargs["player"].player_number == 1:
        opp=player2
    else:
        opp=player1
    opp.souls -= 3
    return True

@psv_check
def play_dead(**kwargs) -> Literal[True]: #passive: on death
    kwargs["origin"].switch_sprite("front")
    kwargs["player"].hand.append(kwargs["origin"].reset())
    return True

#abl_check
def prime(**kwargs) -> Literal[True]: #ability
    opp=None
    if kwargs["player"].player_number == 1:
        opp=player2
    else:
        opp=player1
    if kwargs["origin"].miscs["prime_status"] < 1:
        kwargs["origin"].miscs["prime_status"] += 1
        kwargs["origin"].cut_sprite=transform.rotate(kwargs["origin"].cut_sprite,-90.0)
        tempc=(kwargs["origin"].rect.x,kwargs["origin"].rect.y)
        kwargs["origin"].switch_sprite("cut")
        kwargs["origin"].internal_coords[0], kwargs["origin"].internal_coords[1]=tempc
    elif kwargs["origin"].miscs["prime_status"] == 1:
        for card in opp.field:
            if card != None:
                card.health -= 3
                if "on hurt" in card.passives:
                    card.passives["on hurt"](origin=kwargs["origin"],target=card,damage=3)
        kwargs["origin"].health=0
    return True

@itm_check
def puffer_poison(**kwargs): #item
    if "only_targeting" not in kwargs:
        kwargs["target"].status["psn"] += 1
    else:
        if kwargs["player"] == player1:
            opp=player2
        else:
            opp=player1
        return [card for card in opp.field if card != None]

@atk_check
def purple(**kwargs:Attack_params) -> tuple[Literal[False],int,list[Card]]: #attack
    dmg=0
    if kwargs["noattack"] == False:
        dmg=3
    return False, dmg, [card for card in player1.field+player2.field if card != None]

@psv_check
def quick_strike(**kwargs) -> Literal[True]: #passive: special: quick strike
    if kwargs["origin"].proxy == None:
        intended_target=kwargs["origin"]
    else:
        intended_target=kwargs["origin"].proxy
    intended_target.health -= 1
    if "on hurt" in intended_target.passives:
        intended_target.passives["on hurt"](origin=kwargs["striker"],target=card,damage=1)
    if "on hurt" in intended_target.items:
        for subitem in intended_target.items["on hurt"]:
            subitem.effect(origin=kwargs["striker"],target=card,player=kwargs["player"],damage=1,item=subitem)
    return True

@atk_check
def rush(**kwargs:Attack_params) -> tuple[Literal[True],int]: #attack
    dmg=0
    if kwargs["noattack"] == False:
        dmg=1
    return True, dmg

@psv_check
def self_aid(**kwargs) -> Literal[True]: #passive: end this turn
    kwargs["origin"].heal(1)
    return True

@itm_check
def shield_protect(**kwargs): #item
    if "only_targeting" not in kwargs:
        kwargs["target"].health+=kwargs["original"]
    else:
        return [kwargs["target"]]

@atk_check
def snipe(**kwargs:Attack_params) -> tuple[Literal[False],int]: #attack
    dmg=0
    if kwargs["noattack"] == False:
        dmg=1
    return False, dmg

@atk_check
def spider_bite(**kwargs:Attack_params) -> tuple[Literal[True],int]: #attack
    dmg=0
    if kwargs["noattack"] == False:
        dmg=len([mob for mob in kwargs["player"].field if (mob != None and mob.mob_class == "arthropod")])
    return True, dmg

@psv_check
def split(**kwargs) -> None|tuple[Literal[True],Literal[False]]: #passive: on death
    if kwargs["origin"].miscs["rotation"] == 0:
        kwargs["origin"].health=2
        kwargs["origin"].max_health=2
        kwargs["origin"].cut_sprite=transform.rotate(kwargs["origin"].cut_sprite,-90.0)
        tempc=(kwargs["origin"].rect.x,kwargs["origin"].rect.y)
        kwargs["origin"].switch_sprite("cut")
        kwargs["origin"].internal_coords[0], kwargs["origin"].internal_coords[1]=tempc
        kwargs["origin"].miscs["rotation"]=1
        return (True,False)
    else:
        return None

@psv_check
def spore(**kwargs) -> Literal[True]: #passive: on death
    opp=None
    if kwargs["player"].player_number == 1:
        opp=player2
    else:
        opp=player1
    for card in opp.field:
        if card != None:
            card.status["psn"] += 1
    return True

@atk_check
def squish(**kwargs:Attack_params) -> tuple[Literal[True],int]: #attack
    dmg=0
    if kwargs["noattack"] == False:
        dmg=2-kwargs["origin"].miscs["rotation"]
    return True, dmg

@itm_check
def sword_slash(**kwargs): #item
    if "only_targeting" not in kwargs:
        kwargs["original"][1]+=1
        return kwargs["original"]
    else:
        return [kwargs["target"]]

@psv_check
def thorn_body(**kwargs) -> Literal[True]: #passive: on hurt
    kwargs["origin"].health-=1
    return True

@atk_check
def tongue_whip(**kwargs) -> tuple[Literal[True],int]: #attack
    global until_end
    global selected
    global targets
    global markers
    global hide_large
    dmg=0
    if kwargs["noattack"] == False:
        dmg=1
        if kwargs["target"].items == {}:
            pass
        elif len_items(kwargs["target"].items) == 1:
            kwargs["origin"].add_item(list(kwargs["target"].items.values())[0][0])
            kwargs["target"].remove_item(list(kwargs["target"].items.values())[0][0])
        else:
            until_end += 3
            targets = kwargs["target"].items
            selected=kwargs["origin"]
            hide_large=False
            markers["item stealing"]=(True, kwargs["origin"])
    return True, dmg

@itm_check
def trident_stab(**kwargs): #item
    if "only_targeting" not in kwargs:
        kwargs["original"][0]=False
        kwargs["original"][1]+=1
        return kwargs["original"]
    else:
        return [kwargs["target"]]

@psv_check
def undead(**kwargs) -> Literal[True]|None: #passive: on hurt
    if (kwargs["target"].health+kwargs["damage"]) == kwargs["target"].max_health and kwargs["damage"] >= kwargs["target"].max_health:
        kwargs["target"].health=1
        return True

@atk_check
def warding_laser(**kwargs:Attack_params) -> tuple[Literal[False],int]: #attack
    dmg=0
    if kwargs["noattack"] == False:
        opp=None
        if kwargs["player"].player_number == 1:
            opp=player2
        else:
            opp=player1
        dmg=abs(opp.field.index(kwargs["target"])-kwargs["player"].field.index(kwargs["origin"]))+1
    return False, dmg

#abl_check
def witch_healing(**kwargs) -> Literal[True]: #ability
    global until_end
    if kwargs["origin"].miscs["heal_count"] == 1:
        until_end=0
        kwargs["origin"].miscs["heal_count"]=0
    elif kwargs["origin"].miscs["heal_count"] == 0:
        until_end=1
        kwargs["origin"].miscs["heal_count"]=1
    kwargs["target"].heal(1)
    return True

#abl_check
def witch_poison(**kwargs) -> Literal[True]: #ability
    global until_end
    if kwargs["origin"].miscs["poison_count"] == 1:
        kwargs["origin"].miscs["poison_count"]=0
        until_end=0
    elif kwargs["origin"].miscs["poison_count"] == 0:
        kwargs["origin"].miscs["poison_count"]=1
        until_end=1
    kwargs["target"].status["psn"]+=1
    return True

#abl_check
def wool_guard(**kwargs) -> tuple[Literal[True],Literal["break"]]|None: #ability
    if kwargs["origin"] != kwargs["target"]:
        if kwargs["origin"].proxy_for != None:
            kwargs["origin"].proxy_for.proxy = None
        kwargs["origin"].proxy_for=kwargs["target"]
        kwargs["target"].proxy=kwargs["origin"]
        kwargs["origin"].internal_coords[0]=kwargs["target"].rect.x
        kwargs["origin"].internal_coords[1]=kwargs["target"].rect.y+copysign(40,1.5-kwargs["player"].player_number)
        if kwargs["origin"].proxy != None:
            kwargs["origin"].proxy.proxy_for=None
            kwargs["origin"].proxy.internal_coords[0], kwargs["origin"].proxy.internal_coords[1]= player1.field_pos[player1.field.index(kwargs["origin"].proxy)]
            kwargs["origin"].proxy=None
        return True,"break"
#endregion

#region constants
infofile=open(r"Assets\d_info.hex","rb")
player_infofile=open(r"Assets\p_info.hex","rb")
infojson:dict[str,dict]=json.loads(b.unhexlify(infofile.read()))
playerjson:dict[str,dict]=json.loads(b.unhexlify(player_infofile.read()))
layouts=[LayoutTile("partitioned",mjgs.render("Partitioned",True,(0,0,0)),(90,40),70,50,(930,10),(100,262),(window_dim[0]/2-mjgs.size("Partitioned")[0]/2-160,200),False,"left",(760,210),None,transform.scale(image.load(r"Assets\partitioned_preview.png"),(300,106)).convert()),LayoutTile("centred",mjgs.render("Centred",True,(0,0,0)),(400,140),90,0,(500,100),(1200,330),(window_dim[0]/2-mjgs.size("Centred")[0]/2-160,500),True,"centre",(80,250),[(760,683),(760,-100)],transform.scale(image.load(r"Assets\centred_preview.png"),(300,176)).convert())]
chosen_layout_name:str=playerjson["layout"]
chosen_layout=layouts[[layout.name for layout in layouts].index(chosen_layout_name)]
title_img=transform.scale(image.load(r"Assets\title.png"),(842,120)).convert_alpha()
card_dim=(150,225)
card_dim_rot=(225,150)
cut_dim=(169,172)
item_dim=(75,75)
token_dim=(30,30)
soul=transform.scale(image.load(r"Assets\soul.png"),token_dim).convert()
heart=transform.scale(image.load(r"Assets\hearts_1.png"),(60,60)).convert()
ORANGE = (255,180,0)
SOUL_COLOUR=(255,255,255)
M_BLUE=(50,190,220)
starting_cards=5
drawing_cards=2
background=transform.scale(image.load(r"Assets\background.png"),window_dim).convert()
FPS=60
clock=time.Clock()
fields_anchor=chosen_layout.field_anchor
card_spacing_x=chosen_layout.x_spacing
card_spacing_y=chosen_layout.y_spacing
y_rails=[fields_anchor[1],fields_anchor[1]+card_spacing_y*2+card_dim_rot[1]+cut_dim[1]]
x_rails=[fields_anchor[0],fields_anchor[0]+cut_dim[0]+card_spacing_x,fields_anchor[0]+cut_dim[0]*2+card_spacing_x*2]
hearts_rails=[y_rails[0]+cut_dim[0]+10,y_rails[1]-10-20] #0: player 2, 1: player 1
if chosen_layout.hand_anchor == chosen_layout.field_anchor:
    hand_anchors=[(fields_anchor[0],y_rails[1]+cut_dim[1]+card_spacing_y),(fields_anchor[0],fields_anchor[1]/2-card_dim[1]+10)]
else:
    hand_anchors=chosen_layout.hand_anchor
large_image_pos = chosen_layout.large_image_pos
deck_plc_pos = chosen_layout.deck_plc_pos
subturn_indic_pos = chosen_layout.subturn_indic_pos
game_overs=("win", "tie", "lose")
PORT="0"
effect_sprites={"psn":image.load(r"Assets\psn.png").convert_alpha(),"aquatised":transform.scale(image.load(r"Assets\aquatised.png"),(23,23)).convert()}
monkey_sprite=transform.scale(image.load(r"Assets\monkey.png"),(840*(window_dim[1]/859),window_dim[1])).convert_alpha()
subturn_sprites=[transform.scale(image.load(r"Assets\abs_subturn_none.png"),(150,360)).convert_alpha(),transform.scale(image.load(r"Assets\abs_subturn_1.webp"),(150,360)).convert_alpha(),transform.scale(image.load(r"Assets\abs_subturn_2.webp"),(150,360)).convert_alpha(),transform.scale(image.load(r"Assets\abs_subturn_3.png"),(150,360)).convert_alpha()]
#sys.excepthook=excepthook
game_id=str(int(tm.time()))
colour_wheel=transform.scale(image.load(r"Assets\colour_wheel.png").convert_alpha(),(70,70))
colour_wheel_rect=Rect(window_dim[0]-90,20,70,70)
cards_sidebar_button=transform.scale(image.load(r"Assets\cards_sidebar.png"),(70,70)).convert_alpha()
cards_sidebar_rect=Rect((window_dim[0]-95,115),(70,70))
cards_sidebar_up=transform.rotate(cards_sidebar_button,-90)
cards_sidebar_up_rect=Rect((cards_sidebar_rect.x-window_dim[0]/2,cards_sidebar_rect.y+120),(70,70))
cards_sidebar_down=transform.rotate(cards_sidebar_button,90)
cards_sidebar_down_rect=Rect((cards_sidebar_rect.x-window_dim[0]/2,cards_sidebar_rect.y+230),(70,70))
cards_sidebar_page=0
deck_up:Rect=Rect(450,30,70,70)
deck_down:Rect=Rect(950,30,70,70)
items_left=(transform.scale(cards_sidebar_button,(40,40)),Rect(130,380,40,40))
items_right=(transform.scale(transform.rotate(cards_sidebar_button,180),(40,40)),Rect(200,380,40,40))
all_cut:list[list[Surface]]=[]
all_cut_fulls:list[list[Surface]]=[]
all_cut_names:list[list[str]]=[]
temp=[[],[],[]]
temp_n=0
cuts:list[os.DirEntry]=[file for file in os.scandir("Cut Sprites")]
cut_fulls:list[os.DirEntry]=[file for file in os.scandir("Sprites")]
cut_fulls_names:list[str]=[file.name.split(".")[0] for file in cut_fulls]
for i in range(len(cuts)):
    temp[0].append(transform.scale(image.load(f"Cut Sprites\\{cuts[i].name}"),cut_dim).convert())
    if cuts[i].name.split(".")[0] in cut_fulls_names:
        temp[1].append(transform.scale(image.load(f"Sprites\\{cut_fulls[i].name}"),(card_dim[0]*3,card_dim[1]*3)).convert())
    else:
        temp[1].append(transform.scale(image.load(f"Cut Sprites\\{cuts[i].name}"),(card_dim[0]*3,card_dim[1]*3)).convert())
    temp[2].append("_".join(cuts[i].name.split(".")[0].split(" ")).lower())
    temp_n+=1
    if temp_n == 9 or cuts[i] == cuts[-1]:
        temp_n=0
        all_cut.append(temp[0])
        all_cut_fulls.append(temp[1])
        all_cut_names.append(temp[2])
        temp=[[],[],[]]
temp=[]
all_cut_rects:list[list[Rect]]=[]
for page in all_cut:
    for i in range(len(page)):
        temp.append(Rect((800+(i%3)*(60+cut_dim[0]),145+(i//3)*(20+cut_dim[1])),cut_dim))
    all_cut_rects.append(temp)
    temp=[]
deck_cards_pos=[(20+cut_dim[0])*i+20 for i in range(10)]
settings_button:tuple[Surface,Rect]=(transform.scale(image.load(r"Assets\settings.png"),(70,70)).convert_alpha(),Rect(window_dim[0]-70,0,70,70))
card_bgs_raw=[file for file in os.scandir(r"Assets\Backs")]
card_bgs:list[BGTile]=[]
for i in range(len(card_bgs_raw)):
    card_bgs.append(BGTile(transform.scale(image.load(f"Assets\\Backs\\{card_bgs_raw[i].name}"),card_dim),f"Assets\\Backs\\{card_bgs_raw[i].name}",card_bgs_raw[i].name.split(".")[0].capitalize(),(50+(card_dim[0]+50)*(i%8),100+(card_dim[1]+75)*(i//8))))
thinking=transform.scale(image.load(r"Assets\thinking.png"),(50,50)).convert_alpha()
thinking_progress:int=0
#ai_delay=lambda: randint(1,5)
ai_delay=lambda: 0.5
hand_size_limit=9
#endregion

#region variables
running=True
state="menu"
connect_state="idle"
deck=[]
turn=0
setup=True
subturn=1 #subturn numbers start from 1, keeps track of which card should be attacking
abs_subturn=1 #keeps track of how many subturns have passed
postsubturn=1 #postsubturn numbers start from 1
attack_choosing_state=False
HOST='172.20.16.200'
sock:socket.socket=''
markers={"retry":False, "deck built":False, "do not connect":True, "start of turn called":False, "not enough souls":[0,0,0,0], "data received, proceed":False, "just chose":False, "finishable":True, "freeze":False, "fade":[0,[0,0,0],0,0,0], "game over called":False,"start of move called":False,"item stealing":(False, None),"forage":False,"monkey":0,"until end just changed":False,"concede":None,"await p2":False,"disconnecting":False,"just selected":False,"uninstalling":False,"name sent":False,"sock closed":False,"you timeout":False}
selected=None #card displayed on the side
selected_move=None #move that has been selected
attack_progressing=False #is it the attack target choosing stage
move_hovering_over:tuple[Rect,Callable]|tuple[Rect,Surface,Rect,int,int]=None #tuple of Rect of attack being hovered over and attack function itself, used for click detection
targets=[]
until_end=0
ability_selected=False
selected_deck:None|DeckPreset=None
selected_large=None
deleting_deck=False
editing_deck_title=False
choosing_colour=False
cards_sidebar=False
coord_tooltip=False
linger_anims:list[tuple[Surface,Coord,int,int,Literal["inverse down"]|Literal["inverse up"],int]]=[] #Surface to blit, anchor, end position, current frame, max frames,animation style.
deck_offset=0
last_screen=None
sock_read:bytes=None
disconnect_cd=600
name_changing=False
subsetting=None
chosen_card_bg=playerjson["chosen card bg"]
cardback=transform.scale(image.load(f"Assets\\Backs\\{chosen_card_bg.lower()}.png"),card_dim).convert_alpha()
ai_wait_until:float|int=0
hide_large=False
large_hideable=chosen_layout.large_hideable
hand_fill_type=chosen_layout.hand_fill_type
large_image=None
read_buffer:list[bytes]=[]
write_buffer:list[str]=[]
player2name:str=None
next_send_g:int=0
p2_progress_turn:bool=False
#endregion

#region card definitions
#Note: cards for deck use are defined by deckbuilder(), which takes these strings and eval()s them into objects
#This is so each deck entry has a separate memory value
deck_plc=Item("Deck Placeholder",0,None,transform.rotate(cardback,90),deck_plc_pos,transform.rotate(cardback,90),None,card_dim_rot,'',None,None)
whole_field=Item("THE ENTIRE FIELD!!!",0,nofunction_item,r"Assets\Whole Field.png",(fields_anchor[0],fields_anchor[1]),r"Assets\Whole Field.png","pink",(3*cut_dim[0]+3*card_spacing_x,2*cut_dim[1]+card_dim_rot[1]+2*card_spacing_y),None,None,None)
preset_dummy=Mob("Dummy",0,999,[],[bite],{},{},"misc","plains","pink",r"Sprites\Dummy.png",(0,0),r"Cut Sprites\Dummy.png",[(987,512,1323,579)])
axolotl=r'Mob("Axolotl",3,3,[],[bite],{"on death":play_dead},{},"aquatic","ocean","blue",r"Sprites\Axolotl.png",(0,0),r"Cut SPrites\Axolotl.png",[(57,412,393,479)],1)'
bogged=r'Mob("Bogged",3,3,[],[snipe],{"on death":spore},{},"undead","swamp","blue",r"Sprites\Bogged.webp",(0,0),r"Cut Sprites\Bogged.jpg",[(57,422,393,479)],2)'
bread=r'Item("Bread",1,bread_heal,r"Sprites\Bread.png",(0,0),r"Cut Sprites\Bread.png","blue",card_dim,"when played",1,"all healable",3)'
cake=r'Item("Cake",2,cake_heal,r"Sprites\Cake.png",(0,0),r"Cut Sprites\Cake.png","blue",card_dim,"when played",1,"your field",4)'
cow=r'Mob("Cow",3,4,[Ability(1,milk_share,"can be healed","Milk Share")],[rush],{},{},"misc","plains","blue",r"Sprites\Cow.png",(0,0),r"Cut Sprites\Cow.png",[(57,345,393,402),(57,402,393,469)],5)'
chicken=r'Mob("Chicken",1,2,[],[rush],{"on this turn":mystery_egg},{},"misc","plains","blue",r"Sprites\Chicken.png",(0,0),r"Cut Sprites\Chicken.png",[(57,412,393,479)],6)'
creeper=r'Mob("Creeper",2,2,[Ability(0,prime,"player2 field","Prime")],[],{},{},"misc","cavern","blue",r"Sprites\Creeper.png",(0,0),r"Cut Sprites\Creeper.png",[(57,345,393,452)],7,prime_status=0)'
drowned=r'Mob("Drowned",2,4,[],[drown],{},{},"aquatic","ocean","blue",r"Sprites\Drowned.png",(0,0),r"Cut Sprites\Drowned.png",[(57,397,393,464)],8)'
dummy=r'Mob("Dummy",0,999,[],[bite],{},{},"misc","plains","pink",r"Sprites\Dummy.png",(0,0),r"Cut Sprites\Dummy.png",[(57,412,393,479)],9)'
elder=r'Mob("Elder",6,6,[],[warding_laser],{"end of turn":elders_curse},{},"aquatic","ocean","pink",r"Sprites\Elder.png",(0,0),r"Cut Sprites\Elder.png",[(57,422,393,489)],10)'
egg_rain=r'Item("Egg Rain",1,egg_rain_activate,r"Sprites\Egg Rain.png",(0,0),r"Cut Sprites\Egg Rain.png","blue",card_dim,"on action",1,"opp field",11)'
frog=r'Mob("Frog",2,3,[],[tongue_whip],{},{},"aquatic","swamp","blue",r"Sprites\Frog.png",(0,0),r"Cut Sprites\Frog.png",[(57,412,393,479)],12)'
goat_horn=r'Item("Goat Horn",3,goat_horn_bounce,r"Sprites\Goat Horn.png",(0,0),r"Cut Sprites\Goat Horn.png","pink",card_dim,"when played",1,"special: goat horn",13)'
guardian=r'Mob("Guardian",4,3,[],[eye_laser],{"on hurt":thorn_body},{},"aquatic","ocean","blue",r"Sprites\Guardian.png",(0,0),r"Cut Sprites\Guardian.png",[(57,402,393,469)],14)'
horse=r'Mob("Horse",4,5,[],[bite],{"special: quick strike":quick_strike},{},"misc","plains","pink",r"Sprites\Horse.png",(0,0),r"Cut Sprites\Horse.png",[(57,412,393,479)],15)'
loot_chest=r'Item("Loot Chest",0,loot_chest_draw,r"Sprites\Loot Chest.png",(0,0),r"Cut Sprites\Loot Chest.png","blue",card_dim,"when played",1,"whole field",16)'
milk=r'Item("Milk",2,milk_cleanse,r"Sprites\Milk.png",(0,0),r"Cut Sprites\Milk.png","blue",card_dim,"when played",1,"your field",17)'
muddy_pig=r'Mob("Muddy Pig",2,3,[],[rush],{"on this turn":forage},{},"misc","plains","blue",r"Sprites\Muddy Pig.png",(0,0),r"Cut Sprites\Muddy Pig.png",[(57,412,393,479)],18)'
pufferfish=r'Item("Pufferfish",2,puffer_poison,r"Sprites\Pufferfish.png",(0,0),r"Cut Sprites\Pufferfish.png","blue",card_dim,"when played",1,"whole field",19)'
satoru_gojo='Mob("Satoru Gojo",9,20,[Ability(0,nah_id_win,"whole field","Nah, I\'d Win")],[purple],{"on hurt":infinity},{},"misc","plains","pink",r"Sprites\\Satoru Gojo.png",(0,0),r"Cut Sprites\\Satoru Gojo.png",[(57,402,393,454),(57,454,393,514)],20)'
sheep=r'Mob("Sheep",3,4,[Ability(0,wool_guard,"can proxy","Wool Guard")],[rush],{},{},"misc","plains","blue",r"Sprites\Sheep.png",(0,0),r"Cut Sprites\Sheep.png",[(57,347,393,399),(57,399,393,454)],21)'
shield=r'Item("shield",2,shield_protect,r"Sprites\Shield.png",(0,0),r"Cut Sprites\Shield.png","blue",card_dim,"on hurt",1,"your field",22)'
skeleton=r'Mob("Skeleton",2,3,[],[snipe],{"on hurt":undead},{},"undead","cavern","blue",r"Sprites\Skeleton.png",(0,0),r"Cut Sprites\Skeleton.png",[(57,412,393,469)],23)'
slime=r'Mob("Slime",3,4,[],[squish],{"on death":split},{},"misc","swamp","blue",r"Sprites\Slime.png",(0,0),r"Cut Sprites\Slime.png",[(57,437,393,509)],24,rotation=0)'
spider=r'Mob("Spider",1,2,[],[spider_bite],{},{},"arthropod","cavern","blue",r"Sprites\Spider.png",(0,0),r"Cut Sprites\Spider.png",[(57,412,393,469)],25)'
sunken=r'Mob("Sunken",2,3,[],[snipe],{},{},"aquatic","ocean","blue",r"Sprites\Sunken.png",(0,0),r"Cut Sprites\Sunken.png",[(57,397,393,454)],26)'
sword=r'Item("Sword",1,sword_slash,r"Sprites\Sword.png",(0,0),r"Cut Sprites\Sword.png","blue",card_dim,"on attack",1,"your field",27)'
toji=r'Mob("Toji",9,20,[Ability(0,monkey,"whole field","Monkey!")],[knife_thing],{"always":child_support_avoider},{},"undead","plains","pink",r"Sprites\Toji.png",(0,0),r"Cut Sprites\Toji.png",[(57,397,393,454),(57,454,393,514)],28)'
trident=r'Item("Trident",2,trident_stab,r"Sprites\Trident.png",(0,0),r"Cut SPrites\Trident.png","pink",card_dim,"on attack",1,"your field",29)'
witch=r'Mob("Witch",3,4,[Ability(1,witch_poison,"player2 field","Poison"),Ability(1,witch_healing,"player1 field","Heal")],[],{"end this turn":self_aid},{},["human"],"swamp","blue",r"Sprites\Witch.png",(0,0),r"Cut Sprites\Witch.png",[(57,397,393,469),(57,469,393,539)],30,poison_count=0,heal_count=0)'
zombie=r'Mob("Zombie",2,4,[],[bite],{"on hurt":undead},{},"undead","cavern","blue",r"Sprites\Zombie.png",(0,0),r"Cut Sprites\Zombie.png",[(57,412,393,479)],31)'
#Mob()
#endregion

#region deck stuff
all_cards=[axolotl,bogged,bread,cake,cow,chicken,creeper,drowned,dummy,elder,egg_rain,frog,goat_horn,guardian,horse,loot_chest,milk,muddy_pig,pufferfish,satoru_gojo,sheep,shield,skeleton,slime,spider,sunken,sword,toji,trident,witch,zombie]
all_ids={eval(card).id_num:card for card in all_cards}
tiles:list[dict[str,Tile]]=[{all_cut_names[i][j]:Tile(all_cut_names[i][j],all_cut_fulls[i][j],all_cut[i][j],type(eval(eval(all_cut_names[i][j]))).__name__,eval(eval(all_cut_names[i][j])).border,all_cut_rects[i][j]) for j in range(len(all_cut[i]))} for i in range(len(all_cut))]
d_tiles:dict[str,Tile]={}
for sub in tiles:
    d_tiles.update(sub)
deck_presets:list[DeckPreset]=[]
unpack()
chosen_deck_name=infojson.pop("<chosen>")
for deck in deck_presets:
    if deck.name == chosen_deck_name:
        chosen_deck=deck
decklist_p1={"mobs":{eval(mob):chosen_deck.original_mobs[mob] for mob in chosen_deck.original_mobs},"items":{eval(item):chosen_deck.original_items[item] for item in chosen_deck.original_items}}
decklist_p2={"mobs":{zombie:8},"items":{sword:10}}
deck_p1 = {"mobs":deckbuilder(decklist_p1["mobs"]),"items":deckbuilder(decklist_p1["items"])}
deck_p2 = {"mobs":deckbuilder(decklist_p2["mobs"]),"items":deckbuilder(decklist_p2["items"])}
playername=playerjson["name"]
player1=Player(playername,1,hand_anchors[0],[(x_rails[0],y_rails[1]),(x_rails[1],y_rails[1]),(x_rails[2],y_rails[1])])
player2:Player=''
#endregion

#region texts
beta_text=mjgs.render("Closed Beta",True,(255,100,0))
connect_text=ClickableText(mjgs,"Join Game",(0,0,0),(window_dim[0]/2-mjgs.size("Join Game")[0]/2,650))
connecting_text=mjgs.render("Waiting for connection",True,(255,0,0))
ip_submit_text=ClickableText(mjgs,"Connect",(0,0,0),(window_dim[0]/2-mjgs.size("Connect")[0]/2,750))
pregame_text=mjgs.render("Loading...",True,(0,0,0))
retry_text=mjgs.render("Retry Connection",True,(255,0,0))
game_plc_text=mjgs.render("Await further programming",True,(0,0,0))
win_text=large_font.render("You won!",True,(240,140,240))
lose_text=large_font.render("You lost...",True,(255,0,0))
skill_issue_text=small_font.render("skill issue",True,(255,255,255))
tie_text=large_font.render("You tied!",True,(255,255,0))
to_menu_text=ClickableText(mjgs,"Back to menu",(255,255,255),(window_dim[0]/2-mjgs.size("Back to menu")[0]/2,3*window_dim[1]/4))
decks_text=ClickableText(mjgs,"Decks",(0,0,0),(window_dim[0]/2-mjgs.size("Decks")[0]/2,750))
decks_to_menu_text=ClickableText(mjgs,"Back to menu",(0,0,0),(window_dim[0]/2-mjgs.size("Back to menu")[0]/2,750))
decks_title_text=large_font.render("My Decks",True,(0,0,0))
create_deck_text=ClickableText(mjgs,"+ Create new deck",(20,100,140),(window_dim[0]-mjgs.size("+ Create new deck")[0]-100,750))
delete_deck_text=ClickableText(mjgs,"Delete deck",(200,0,0),(100,750))
deck_inspects_to_presets_text=ClickableText(mjgs,"Back",(255,0,0),(100,750))
deck_mobs_text=mjgs.render("Mobs:",True,(0,0,0))
deck_items_text=mjgs.render("Items:",True,(0,0,0))
select_deck_text=ClickableText(mjgs,"Use deck",(0,255,0),(window_dim[0]-mjgs.size("Use deck")[0]-100,750))
deck_selected_text=mjgs.render("Deck selected",True,(180,180,180))
deck_unusable_text=mjgs.render("Use deck",True,(180,180,180))
if chosen_deck.usable:
    menu_selected_deck_text=mjgs.render("Selected deck:",True,(0,0,0))
else:
    menu_selected_deck_text=mjgs.render("Selected deck:",True,(255,0,0))
menu_deck_selected_text=mjgs.render(chosen_deck.name,True,contrast(chosen_deck.colour))
deck_unusable_warning=mjgs.render("This deck is not usable",True,(200,0,0))
opp_conc_text=large_font.render("Opponent conceded",True,(240,140,240))
you_conc_text=large_font.render("You conceded",True,(255,0,0))
conc_text=ClickableText(mjgs,"Concede",(255,0,0),(window_dim[0]/2-mjgs.size("Concede")[0]/2,window_dim[1]/2))
settings_text=large_font.render("Settings",True,(0,0,0))
name_change_text=ClickableText(mjgs,"Change name",(0,0,0),(window_dim[0]/2,150))
to_profile_text=ClickableText(mjgs,"Profile",(0,0,0),(window_dim[0]/2-mjgs.size("Profile")[0]/2,200))
to_bg_cstm_text=ClickableText(mjgs,"Change background",(0,0,0),(window_dim[0]/2-mjgs.size("Change background")[0]/2,400))
settings_back_text=ClickableText(mjgs,"Back",(0,0,0),(window_dim[0]/2-mjgs.size("Back")[0]/2,750))
playername_text=mjgs.render(f"Name: {playername}",True,(0,0,0))
cardbg_change_text=ClickableText(mjgs,"Change card back",(0,0,0),(window_dim[0]/2-mjgs.size("Change card back")[0]/2,300))
change_game_layout_text=ClickableText(mjgs,"Change game layout",(0,0,0),(window_dim[0]/2-mjgs.size("Change game layout")[0]/2,500))
connecting_back_text=ClickableText(mjgs,"Back",(0,0,0),(window_dim[0]/2-mjgs.size("Back")[0]/2,810))
uninstall_text=ClickableText(mjgs,"Uninstall",(255,0,0),(window_dim[0]/2-mjgs.size("Uninstall")[0]/2,600))
uninstall_warn_text_1=mjgs.render("Warning: Uninstalling is permanent.",True,(0,0,0))
uninstall_warn_text_2=mjgs.render("Your files will not be recoverable from the Recycle Bin.",True,(0,0,0))
uninstall_warn_text_3=mjgs.render("Do you want to proceed?",True,(0,0,0))
uninstall_cancel_text=ClickableText(mjgs,"No",(0,255,0),(window_dim[0]/3-mjgs.size("No")[0]/2,550))
uninstall_confirm_text=ClickableText(mjgs,"Yes",(255,0,0),(2*window_dim[0]/3-mjgs.size("Yes")[0]/2,550))
uninstalling_text=large_font.render("Uninstalling...",True,(0,0,0))
singleplayer_text=ClickableText(mjgs,"Singleplayer",(0,0,0),(window_dim[0]*11/18-mjgs.size("Singleplayer")[0]/2,550))
multiplayer_text=ClickableText(mjgs,"Multiplayer",(0,0,0),(window_dim[0]*7/18-mjgs.size("Multiplayer")[0]/2,550))
you_timeout_text=large_font.render("You timed out",True,(255,0,0))
opp_timeout_text=large_font.render("Opponent timed out",True,(240,140,240))
#endregion

while running:
    screen.blit(background,(0,0))
    if markers["uninstalling"]:
        uninstall(os.getcwd())
    if markers["monkey"] != 0:
        screen.blit(monkey_sprite,(window_dim[0]-(markers["monkey"]/60)*window_dim[0],0))
        markers["monkey"] -= 1
    if type(sock) == socket.socket:
        read_ready, write_ready, error_ready=select.select([sock],[sock],[],0)
        if sock in read_ready:
            if state == "menu" and connect_state == "hosting":
                sock, addr= sock.accept()
                print(f"{'\033[96m'}Accepted connection at {addr}{'\033[0m'}")
                state="pregame"
            else:
                try:
                    sock_read=sock.recv(1024)
                except IOError as e:
                    if e.errno == 10053 or e.errno == 10054:
                        disconnect_cd=0
                        markers["disconnecting"]=True
                        print(f"{'\033[93m'}Err. 10053/4: Concede indicated by disconnect{'\033[0m'}")
                    else:
                        print(f"{'\033[91m'}{str(e)}{'\033[0m'}")
                else:
                    for datum in sock_read.split("END".encode()):
                        if datum != ''.encode():
                            read_buffer.append(datum)
                        #print(read_buffer)
        if sock in write_ready and write_buffer != []:
            sock.send(write_buffer.pop(0).encode())
        if sock in error_ready:
            raise RuntimeError(f"Mom, sockets are acting up again!\n{sock.error}")
        if tm.time() > next_send_g and state == "game":
            if False not in [card.playable for card in player1.hand]:
                write_buffer.append("xEND")
            else:
                write_buffer.append("gEND")
            next_send_g=tm.time()+1
    if markers["do not connect"]:
        temp, p2_progress_turn=execute(sock_read)
        sock_read="gEND".encode()
        if setup:
            temp=False
    elif read_buffer != []:
        temp, p2_progress_turn=execute(read_buffer.pop(0))
    if type(temp) == bool:
        markers["await p2"]=temp
    if p2_progress_turn:
        if until_end <= 0 and next_turn:
            corr_subturn=list(filled_positions.keys())[abs_subturn%len(filled_positions)]
            if player2.field[corr_subturn-1] != None:
                if "end this turn" in player2.field[corr_subturn-1].passives:
                    player2.field[corr_subturn-1].passives["end this turn"](origin=player2.field[corr_subturn-1],player=player2,loc=(player2.field[corr_subturn-1].rect.x,player2.field[corr_subturn-1].rect.y+cut_dim[1]/2))
                if player2.field[corr_subturn-1].status["psn"] > 0:
                    player2.field[corr_subturn-1].hurt(1,"psn")
                    player2.field[corr_subturn-1].status["psn"] -= 1
        elif until_end > 0:
            until_end -= 1
            markers["until end just changed"]=True
            markers["await p2"]=True
        p2_progress_turn=False

    for e in event.get():
        if e.type == QUIT and not markers["uninstalling"]:
            if type(sock) == socket.socket:
                sock.close()
            infofile.close()
            infofile=open(r"Assets\d_info.hex","wb")
            final_json={x[0]:x[1] for x in [preset.to_dict() for preset in deck_presets]}
            final_json.update({"<chosen>":chosen_deck.name})
            infofile.write(b.hexlify(json.dumps(final_json).encode()))
            infofile.close()
            player_infofile.close()
            player_infofile=open(r"Assets\p_info.hex","wb")
            playerjson["name"]=playername
            playerjson["chosen card bg"]=chosen_card_bg
            playerjson["layout"]=chosen_layout_name
            player_infofile.write(b.hexlify(json.dumps(playerjson).encode()))
            player_infofile.close()
            running=False

        if e.type == MOUSEBUTTONUP and state not in game_overs:
            pos:Coord=mouse.get_pos()
            if settings_button[1].collidepoint(pos) and selected_deck == None and not markers["uninstalling"]:
                if state == "settings":
                    state = last_screen
                    subsetting=None
                else:
                    last_screen = state
                    state = "settings"

        if e.type == MOUSEBUTTONUP and state == "settings":
            if settings_back_text.textrect.collidepoint(pos):
                if subsetting == None:
                    state=last_screen
                if subsetting == "profile":
                    name_changing=False
                subsetting=None
            elif conc_text.textrect.collidepoint(pos) and last_screen == "game" and state not in game_overs:
                markers["concede"]="you"
                setup=False
                state="lose"
                write_buffer.append("cEND")
            elif last_screen == "menu" and subsetting == None:
                if to_profile_text.textrect.collidepoint(pos):
                    subsetting="profile"
                elif to_bg_cstm_text.textrect.collidepoint(pos):
                    subsetting="bg"
                elif cardbg_change_text.textrect.collidepoint(pos):
                    subsetting="cardbg"
                elif change_game_layout_text.textrect.collidepoint(pos):
                    subsetting="layout"
                elif uninstall_text.textrect.collidepoint(pos):
                    subsetting="uninstall"
            elif subsetting == "profile":
                if name_change_text.textrect.collidepoint(pos):
                    name_changing=True
            elif subsetting == "cardbg":
                for bg in card_bgs:
                    if bg.rect.collidepoint(pos):
                        chosen_card_bg=bg.name
                        cardback=transform.scale(image.load(bg.path),card_dim).convert_alpha()
                        deck_plc.current_sprite=transform.rotate(cardback,90)
            elif subsetting == "layout":
                for layout in layouts:
                    if layout.rect.collidepoint(pos):
                        chosen_layout_name=layout.name
                        fields_anchor=layout.field_anchor
                        card_spacing_x=layout.x_spacing
                        card_spacing_y=layout.y_spacing
                        large_image_pos=layout.large_image_pos
                        deck_plc_pos=layout.deck_plc_pos
                        large_hideable=layout.large_hideable
                        hand_fill_type=layout.hand_fill_type
                        y_rails=[fields_anchor[1],fields_anchor[1]+card_spacing_y*2+card_dim_rot[1]+cut_dim[1]]
                        x_rails=[fields_anchor[0],fields_anchor[0]+cut_dim[0]+card_spacing_x,fields_anchor[0]+cut_dim[0]*2+card_spacing_x*2]
                        if layout.hand_anchor == layout.field_anchor:
                            hand_anchors=[(fields_anchor[0],y_rails[1]+cut_dim[1]+card_spacing_y),(fields_anchor[0],fields_anchor[1]/2-card_dim[1]+10)]
                        else:
                            hand_anchors=layout.hand_anchor
                        hearts_rails=[y_rails[0]+cut_dim[0]+10,y_rails[1]-10-20]
                        subturn_indic_pos=layout.subturn_indic_pos
                        deck_plc=Item("Deck Placeholder",0,None,transform.rotate(cardback,90),deck_plc_pos,transform.rotate(cardback,90),None,card_dim_rot,'',None,None)
                        whole_field=Item("THE ENTIRE FIELD!!!",0,nofunction_item,r"Assets\Whole Field.png",(fields_anchor[0],fields_anchor[1]),r"Assets\Whole Field.png","pink",(3*cut_dim[0]+3*card_spacing_x,2*cut_dim[1]+card_dim_rot[1]+2*card_spacing_y),None,None,None)
            elif subsetting == "uninstall":
                if uninstall_cancel_text.textrect.collidepoint(pos):
                    subsetting=None
                elif uninstall_confirm_text.textrect.collidepoint(pos):
                    if os.getcwd().endswith("Minecards"):
                        markers["uninstalling"]=True

        elif e.type == MOUSEBUTTONUP and state not in game_overs and not markers["freeze"] and not markers["await p2"]:
            pos:Coord=mouse.get_pos()
            next_turn=False
            if state == "menu":
                if singleplayer_text.textrect.collidepoint(pos) and connect_state == "idle":
                    markers["do not connect"]=True
                    if chosen_deck.usable:
                        state="game"
                        player2=Player("Player 2",2,hand_anchors[1],[(x_rails[0],y_rails[0]),(x_rails[1],y_rails[0]),(x_rails[2],y_rails[0])])
                    else:
                        linger_anims.append([deck_unusable_warning,(window_dim[0]/2-deck_unusable_warning.get_width()/2,400),0,120,"inverse down",0])
                    player1=Player(playername,1,hand_anchors[0],[(x_rails[0],y_rails[1]),(x_rails[1],y_rails[1]),(x_rails[2],y_rails[1])])
                elif multiplayer_text.textrect.collidepoint(pos) and connect_state == "idle":
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    HOST=s.getsockname()[0]
                    s.close()
                    sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.setblocking(False)
                    sock.bind((HOST,int(PORT)))
                    sock.listen()
                    connect_state="hosting"
                elif state == "menu" and connect_state == "connecting":
                    if Rect(300,625,900,100).collidepoint(pos):
                        selected="PORT"
                    elif Rect(300,425,900,100).collidepoint(pos):
                        selected="IP"
                    elif ip_submit_text.textrect.collidepoint(pos) and connect_state == "connecting":
                        try:
                            sock.connect((HOST,int(PORT)))
                            state="pregame" #await info to build player2
                            print(f"{'\033[096m'}Connection successful{'\033[0m'}")
                        except Exception as e:
                            print(f"{'\033[91m'}{str(e)}{'\033[0m'}")
                            if e.errno == 10035:
                                print(f"{'\033[93m'}Err. 10035: Skipped as per regulation{'\033[0m'}")
                                state="pregame" #await info to build player2
                                print(f"{'\033[096m'}Connection successful{'\033[0m'}")
                            else:
                                markers["retry"]=True
                elif connect_text.textrect.collidepoint(pos) and connect_state == "idle":
                    sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.setblocking(False)
                    connect_state="connecting"
                elif connecting_back_text.textrect.collidepoint(pos) and connect_state == "connecting":
                    connect_state="idle"
                elif decks_text.textrect.collidepoint(pos):
                    state="deck screen"
                    
            elif state == "settings":
                if settings_back_text.textrect.collidepoint(pos):
                    if subsetting == None:
                        state=last_screen
                    if subsetting == "profile":
                        name_changing=False
                    subsetting=None
                elif conc_text.textrect.collidepoint(pos) and last_screen == "game" and state not in game_overs:
                    markers["concede"]="you"
                    setup=False
                    state="lose"
                    write_buffer.append("cEND")
                elif last_screen == "menu" and subsetting == None:
                    if to_profile_text.textrect.collidepoint(pos):
                        subsetting="profile"
                    elif to_bg_cstm_text.textrect.collidepoint(pos):
                        subsetting="bg"
                    elif cardbg_change_text.textrect.collidepoint(pos):
                        subsetting="cardbg"
                    elif change_game_layout_text.textrect.collidepoint(pos):
                        subsetting="layout"
                    elif uninstall_text.textrect.collidepoint(pos):
                        subsetting="uninstall"
                elif subsetting == "profile":
                    if name_change_text.textrect.collidepoint(pos):
                        name_changing=True
                elif subsetting == "cardbg":
                    for bg in card_bgs:
                        if bg.rect.collidepoint(pos):
                            chosen_card_bg=bg.name
                            cardback=transform.scale(image.load(bg.path),card_dim).convert_alpha()
                            deck_plc.current_sprite=transform.rotate(cardback,90)
                elif subsetting == "layout":
                    for layout in layouts:
                        if layout.rect.collidepoint(pos):
                            chosen_layout_name=layout.name
                            fields_anchor=layout.field_anchor
                            card_spacing_x=layout.x_spacing
                            card_spacing_y=layout.y_spacing
                            large_image_pos=layout.large_image_pos
                            deck_plc_pos=layout.deck_plc_pos
                            large_hideable=layout.large_hideable
                            hand_fill_type=layout.hand_fill_type
                            y_rails=[fields_anchor[1],fields_anchor[1]+card_spacing_y*2+card_dim_rot[1]+cut_dim[1]]
                            x_rails=[fields_anchor[0],fields_anchor[0]+cut_dim[0]+card_spacing_x,fields_anchor[0]+cut_dim[0]*2+card_spacing_x*2]
                            if layout.hand_anchor == layout.field_anchor:
                                hand_anchors=[(fields_anchor[0],y_rails[1]+cut_dim[1]+card_spacing_y),(fields_anchor[0],fields_anchor[1]/2-card_dim[1]+10)]
                            else:
                                hand_anchors=layout.hand_anchor
                            hearts_rails=[y_rails[0]+cut_dim[0]+10,y_rails[1]-10-20]
                            subturn_indic_pos=layout.subturn_indic_pos
                            deck_plc=Item("Deck Placeholder",0,None,transform.rotate(cardback,90),deck_plc_pos,transform.rotate(cardback,90),None,card_dim_rot,'',None,None)
                            whole_field=Item("THE ENTIRE FIELD!!!",0,nofunction_item,r"Assets\Whole Field.png",(fields_anchor[0],fields_anchor[1]),r"Assets\Whole Field.png","pink",(3*cut_dim[0]+3*card_spacing_x,2*cut_dim[1]+card_dim_rot[1]+2*card_spacing_y),None,None,None)
                elif subsetting == "uninstall":
                    if uninstall_cancel_text.textrect.collidepoint(pos):
                        subsetting=None
                    elif uninstall_confirm_text.textrect.collidepoint(pos):
                        markers["uninstalling"]=True

            elif state == "deck screen":
                if decks_to_menu_text.textrect.collidepoint(pos):
                    state="menu"
                    selected_deck=None
                    selected=None
                    selected_large=None
                    chosen_deck.unpack(chosen_deck.mobs,chosen_deck.items,"whitelist",[])
                    if not chosen_deck.usable:
                        menu_selected_deck_text=mjgs.render("Selected deck:",True,(255,0,0))
                    else:
                        menu_selected_deck_text=mjgs.render("Selected deck:",True,(0,0,0))
                elif selected_deck == None:
                    if delete_deck_text.textrect.collidepoint(pos) and deleting_deck == False:
                        deleting_deck=True
                    elif deleting_deck == True:
                        temp=[]
                        for deck in deck_presets:
                            temp.append(deck.deck_delete_clicks(pos))
                        if True not in temp:
                            deleting_deck=False
                            temp2=False
                    elif create_deck_text.textrect.collidepoint(pos):
                        copies=len([deck.name for deck in deck_presets if deck.name == "New Deck"])
                        if copies == 0:
                            name="New Deck"
                        else:
                            name=f"New Deck({copies})"
                        deck_presets.append(DeckPreset(name,max([deck.number for deck in deck_presets])+1,(255,255,255),{},{}))
                        selected_deck=deck_presets[-1]
                    elif deck_up.collidepoint(pos) and deck_offset != 0:
                        deck_offset-=1
                    elif deck_down.collidepoint(pos) and not len(deck_presets)-5*deck_offset < 5:
                        deck_offset+=1
                    else:
                        for preset in deck_presets:
                            if preset.outer_rect.collidepoint(pos):
                                selected_deck=preset
                                preset.unpack(preset.original_mobs,preset.original_items,"whitelist","pinks")
                elif deck_inspects_to_presets_text.textrect.collidepoint(pos):
                    selected=None
                    selected_deck=None
                    selected_large=None
                else:
                    selected_deck.deck_other_clicks(pos)
                    temp=False
                    if selected_deck.title_bg_rect.collidepoint(pos):
                        editing_deck_title=True
                        temp=True
                    elif editing_deck_title == True:
                        editing_deck_title=False
                        temp=True
                    if selected != None:
                        temp=selected_deck.deck_change_clicks(pos)
                        if temp:
                            break
                    for mob in selected_deck.mobs:
                        if mob.rect.collidepoint(pos):
                            selected=mob
                            hide_large=False
                            selected_deck.set_renders(mob.rect)
                            temp=True
                        if not temp:
                            selected=None
                            selected_large=None
                            selected_deck.set_renders(None)
                    for item in selected_deck.items:
                        if item.rect.collidepoint(pos):
                            selected=item
                            hide_large=False
                            selected_deck.set_renders(item.rect)
                            temp=True
                        if not temp:
                            selected=None
                            selected_large=None
                            selected_deck.set_renders(None)
                    if cards_sidebar_rect.collidepoint(pos):
                        cards_sidebar_button=transform.rotate(cards_sidebar_button,180)
                        cards_sidebar_rect.x+=copysign(window_dim[0]/2,int(cards_sidebar)-1)
                        cards_sidebar=not cards_sidebar
                    if cards_sidebar_up_rect.collidepoint(pos) and cards_sidebar_page != 0:
                        cards_sidebar_page-=1
                    if cards_sidebar_down_rect.collidepoint(pos) and cards_sidebar_page != len(all_cut)-1:
                        cards_sidebar_page+=1
                    if move_hovering_over != None:
                        if move_hovering_over[0].collidepoint(pos):
                            selected_large=move_hovering_over[1]
                        elif move_hovering_over[2].collidepoint(pos) and all_cut_names[move_hovering_over[3]][move_hovering_over[4]] not in list(selected_deck.original_mobs.keys())+list(selected_deck.original_items.keys()):
                            if eval(all_cut_names[move_hovering_over[3]][move_hovering_over[4]])[0] == "M":
                                target_tile=list(d_tiles.values())[move_hovering_over[3]*9+move_hovering_over[4]]
                                if (target_tile.border == "pink" and selected_deck.pink_mob == False) or target_tile.border == "blue":
                                    selected_deck.original_mobs[all_cut_names[move_hovering_over[3]][move_hovering_over[4]]]=1
                            else:
                                if (target_tile.border == "pink" and selected_deck.pink_item == False) or target_tile.border == "blue":
                                    selected_deck.original_items[all_cut_names[move_hovering_over[3]][move_hovering_over[4]]]=1
                            selected_deck.unpack(selected_deck.original_mobs,selected_deck.original_items)
                        else:
                            move_hovering_over=None

            elif state == "game" and not attack_progressing:
                for card in player1.field:
                    if card != None and not (large_hideable and not hide_large and large_image.get_rect(x=large_image_pos[0],y=large_image_pos[1]).collidepoint(pos)):
                        if card.rect.collidepoint(pos):
                            selected=card
                            hide_large=False
                            markers["just selected"]=True
                        for item in card.items:
                            for subitem in card.items[item]:
                                if subitem.rect.collidepoint(pos):
                                    selected=subitem
                                    hide_large=False
                                    markers["just selected"]=True
                for card in player1.hand:
                    if card.rect.collidepoint(pos):
                        selected=card
                        hide_large=False
                        markers["just selected"]=True
                for card in player2.field:
                    if card != None:
                        if card.rect.collidepoint(pos):
                            selected=card
                            hide_large=False
                            markers["just selected"]=True
                        for item in card.items:
                            for subitem in card.items[item]:
                                if subitem.rect.collidepoint(pos):
                                    selected=subitem
                                    hide_large=False
                                    markers["just selected"]=True
                for card in player2.hand:
                    if card.rect.collidepoint(pos) and card.current_sprite != card.back_sprite:
                        selected=card
                        hide_large=False
                if move_hovering_over != None and ((not True in [card.rect.collidepoint(mouse.get_pos()) for card in player1.hand+[mob for mob in player1.field if mob != None]+[mob for mob in player2.field if mob != None]] and not large_hideable) or (large_hideable and not hide_large)):
                    if type(selected) == Mob and move_hovering_over[0].collidepoint(pos) and player1.field.index(selected) == subturn-1:
                        selected_move=move_hovering_over[1]
                        if type(selected_move) != Ability:
                            targets=player2.field
                        else:
                            if player1.souls >= selected_move.cost:
                                targets=selected_move.find_targets(selected)
                            else:
                                if markers["not enough souls"][0] == [0]:
                                    markers["not enough souls"]=[6,5,0,0]
                        attack_progressing=True
                        markers["just chose"]=True
                    if type(selected) == Item and move_hovering_over[0].collidepoint(pos) and selected in player1.hand:
                        selected_move=move_hovering_over[1]
                        targets=selected.find_targets()
                        attack_progressing=True
                        markers["just chose"]=True
                for i in range(3):
                    if selected in player1.hand and player1.field[i] == None and Rect(player1.field_pos[i],cut_dim).collidepoint(pos):
                        if selected.cost <= player1.souls and type(selected) == Mob:
                            if not markers["do not connect"]:
                                write_buffer.append("p"+str(player1.hand.index(selected))+str(i)+"END")
                            player1.add_to_field("self",player1.hand.index(selected),i)
                            abs_subturn += 1
                            markers["start of move called"]=False
                            if not setup and markers["do not connect"]:
                                ai_wait_until=tm.time()+ai_delay()
                                markers["await p2"]=True
                            elif not markers["do not connect"]:
                                markers["await p2"]=True
                        else:
                            if markers["not enough souls"][0] == 0 and min(hand_cost) >= player1.souls:
                                markers["not enough souls"]=[6,5,0,0] #[amount of cycles,frames per cycle,current colour,frame number]
                if large_image != None and large_hideable and not large_image.get_rect(left=large_image_pos[0],top=large_image_pos[1]).collidepoint(pos) and not markers["just selected"]:
                    hide_large=True
                markers["just selected"]=False

            elif attack_progressing:
                if type(selected) == Mob and markers["item stealing"][0] == False:
                    for card in targets:
                        if card != None and card.rect.collidepoint(pos) and setup == False:
                            result=None
                            target=card
                            if type(selected_move) != Ability:
                                counter=selected_move(origin=selected,target=target,player=player1,noattack=False)
                                write_buffer.append("m"+str(player1.field.index(selected))+str(selected.moveset.index(selected_move))+str(player2.field.index(target))+"END")
                                if len(target.moveset) > 0:
                                    other_counter=target.moveset[0](origin=target,target=selected,player=player2,noattack=True)
                                else:
                                    counter=False
                                    other_counter=not counter
                                selected.startmove([(target.rect.x,target.rect.y),(selected.rect.x,selected.rect.y)],[10,10])
                                if (counter == True or counter == other_counter) and len(target.moveset) > 0:
                                    card.moveset[0](origin=target,target=selected,player=player2,noattack=False)
                                next_turn=True
                            else:
                                result=selected_move.use(origin=selected,target=target,player=player1,loc=(selected.rect.x,selected.rect.y+cut_dim[1]/2))
                                if selected_move.targets != "whole field":
                                    if target in player1.field:
                                        temp=str(player1.field.index(target))+"2"
                                    else:
                                        temp=str(player2.field.index(target))+"1"
                                else:
                                    temp="3"
                                write_buffer.append("a"+str(player1.field.index(selected))+str(selected.abilities.index(selected_move))+temp+"END")
                                next_turn=True
                            if large_hideable:
                                hide_large=True
                            if until_end == 0:
                                if result == "break":
                                    break
                elif type(selected) == Item and markers["item stealing"][0] == False:
                    for card in targets:
                        if card != None and card.rect.collidepoint(pos) and setup == False and targets != []:
                            if not selected.cost > player1.souls:
                                if card in player1.field:
                                    write_buffer.append("i"+str(player1.hand.index(selected))+str(player1.field.index(card))+"2"+"END")
                                    player1.add_to_field("self",player1.hand.index(selected),player1.field.index(card))
                                elif card in player2.field:
                                    write_buffer.append("i"+str(player2.hand.index(selected))+str(player1.field.index(card))+"1"+"END")
                                    player2.add_to_field("self",selected,player2.field.index(card),ignore_cost=True)
                                    player1.hand.pop(player1.hand.index(selected))
                                    player1.souls -= selected.cost
                                elif targets == [whole_field]:
                                    write_buffer.append("i"+str(player1.hand.index(selected))+"3"+"END")
                                    player1.add_to_field("field",selected,card)
                                next_turn=True
                                if large_hideable:
                                    hide_large=True
                                if until_end > 0:
                                    targets=selected.find_targets()
                            else:
                                if markers["not enough souls"][0] == 0:
                                    markers["not enough souls"]=[6,5,0,0]

                if until_end <= 0 and next_turn:
                    if type(selected) == Item:
                        selected=player1.field[subturn-1]
                    if selected != None:
                        if "end this turn" in selected.passives:
                            selected.passives['end this turn'](origin=selected,player=player1,loc=(selected.rect.x,selected.rect.y))
                        if selected.status["psn"] > 0:
                            selected.hurt(1,"psn")
                            selected.status["psn"] -= 1
                    if postsubturn == 1 and setup == False:
                        abs_subturn += 1
                        ai_wait_until=tm.time()+ai_delay()
                        markers["await p2"]=True
                        markers["start of move called"]=False
                    if abs_subturn != 3:
                        selected = player1.field[abs_subturn%len(filled_positions)]
                    else:
                        selected=player1.field[0]
                        hide_large=False
                        postsubturn += 1
                    attack_progressing=False
                    selected_move=None
                    move_hovering_over=None
                    targets=[]
                elif until_end > 0:
                    until_end -= 1
                    markers["until end just changed"]=True

                if markers["item stealing"][0] == True:
                    for item in targets:
                        if item.rect.collidepoint(pos) and setup == False:
                            for card in player1.field+player2.field:
                                if item in card.items:
                                    target_mob=card
                        markers["item stealing"][1].items[item.condition]=item
                        del target_mob.items[item.condition]
                    markers["item stealing"]=(False, None)
                    attack_progressing=False
                    selected_move=None
                    move_hovering_over=None
                    targets=[]
                    until_end=0
                if not markers["just chose"] and not markers["until end just changed"]:
                    for card in targets:
                        if not(card != None and card.rect.collidepoint(pos) and setup == False):
                            selected_move=None
                            move_hovering_over=None
                            attack_progressing=False
                            targets=[]
                    else:
                        if targets == []:
                            selected_move=None
                            move_hovering_over=None
                            attack_progressing=False
                            targets=[]
                if large_hideable and not large_image.get_rect(x=large_image_pos[0],y=large_image_pos[1]).collidepoint(pos):
                    hide_large=True
                markers["just chose"]=False

        elif e.type == MOUSEBUTTONUP and state in game_overs:
            pos = mouse.get_pos()
            if to_menu_text.textrect.collidepoint(pos):
                sock=''
                state = "menu"
                connect_state="idle"
                deck=[]
                turn=0
                setup=True
                subturn=1
                abs_subturn=1
                postsubturn=1
                attack_choosing_state=False
                HOST=''
                sock=''
                markers={"retry":False, "deck built":False, "do not connect":True, "start of turn called":False, "not enough souls":[0,0,0,0], "data received, proceed":False, "just chose":False, "finishable":True, "freeze":False, "game over called":False, "fade":[0,[0,0,0],0,0,0], "start of move called":False,"item stealing":(False, None),"forage":False,"monkey":0,"until end just changed":False,"concede":None,"await p2":False,"disconnecting":False,"hide large":False,"just selected":False,"uninstalling":False,"name sent":False,"sock closed":False,"you timeout":False}
                selected=None
                hide_large=False
                selected_move=None
                attack_progressing=False
                move_hovering_over=None
                game_id=str(int(tm.time()))
                player2=''
                player1.reset()
                linger_anims=[]
                sock_read=None
                read_buffer=[]
                write_buffer=[]
        
        elif e.type==KEYDOWN:
            if e.key==K_p:
                print(str(mouse.get_pos()))
                coord_tooltip= not coord_tooltip
            '''elif e.key == K_n:
                execute(p2_move(player2.hand,player2.field,player2.souls))'''
            if state == "menu" and connect_state == "connecting":
                if e.key == K_BACKSPACE:
                    if selected == "IP":
                        HOST = HOST[:-1]
                    elif selected == "PORT":
                        PORT=PORT[:-1]
                elif e.key == K_RETURN:
                    selected=None
                else:
                    if selected == "IP":
                        HOST += e.unicode
                    elif selected == "PORT":
                        PORT += e.unicode
            '''if e.key == K_e and connect_state != "connecting" and editing_deck_title == False:
                raise RuntimeError("User called exception.")'''
            if state == "deck screen" and selected_deck != None and editing_deck_title == True:
                selected_deck.edit_title(e)
            if name_changing:
                if e.key == K_BACKSPACE:
                    playername=playername[:-1] 
                elif e.key == K_RETURN or e.key == K_ESCAPE:
                    name_changing=False
                elif len(playername) < 15:
                    playername += e.unicode
                playername_text=mjgs.render(f"Name: {playername}",True,(0,0,0))

    if state == "menu":
        screen.blit(title_img,(window_dim[0]/2-421,165))
        screen.blit(beta_text,(window_dim[0]/2-mjgs.size("Closed Beta")[0]/2,320))
        if connect_state == "idle":
            screen.blit(multiplayer_text.text,multiplayer_text.position)
            screen.blit(singleplayer_text.text,singleplayer_text.position)
            screen.blit(connect_text.text, connect_text.position)
            screen.blit(decks_text.text, decks_text.position)
            screen.blit(menu_selected_deck_text,(950,675))
            draw.rect(screen,chosen_deck.colour,Rect(1090-menu_deck_selected_text.get_width()/2,745,menu_deck_selected_text.get_width()+20,mjgs.get_height()+10))
            screen.blit(menu_deck_selected_text,(1100-menu_deck_selected_text.get_width()/2,750))
        elif connect_state == "hosting":
            screen.blit(connecting_text,(window_dim[0]/2-mjgs.size("Waiting for connection")[0]/2,600))
            temp=sock.getsockname()
            ip_text=mjgs.render("IP: "+str(temp[0]),True,(0,0,0))
            port_text=mjgs.render("Port: "+str(temp[1]),True,(0,0,0))
            screen.blit(ip_text,(window_dim[0]/2-ip_text.get_width()/2,400))
            screen.blit(port_text,(window_dim[0]/2-port_text.get_width()/2,500))
        elif connect_state == "connecting":
            draw.rect(screen,(255,255,255),Rect(300,625,900,100))
            draw.rect(screen,(255,255,255),Rect(300,425,900,100))
            screen.blit(mjgs.render("IP:",True,(0,0,0)),(200,425))
            screen.blit(mjgs.render("PORT:",True,(0,0,0)),(200,625))
            ip_text=mjgs.render(HOST,True,(0,0,0))
            port_text=mjgs.render(str(PORT),True,(0,0,0))
            screen.blit(ip_text,(325,450))
            screen.blit(port_text,(325,650))
            if tm.time()%1>0.5:
                if selected == "IP":
                    draw.rect(screen,(0,0,0),Rect(ip_text.get_size()[0]+325,440,5,70))
                elif selected == "PORT":
                    draw.rect(screen,(0,0,0),Rect(port_text.get_size()[0]+325,640,5,70))
            screen.blit(ip_submit_text.text, ip_submit_text.position)
            screen.blit(connecting_back_text.text,connecting_back_text.position)
            if markers["retry"] == True:
                screen.blit(retry_text,(window_dim[0]/2-mjgs.size("Retry Connection")[0]/2,370))

    elif state == "deck screen":
        screen.blit(decks_to_menu_text.text, decks_to_menu_text.position)
        if selected_deck == None:
            screen.blit(decks_title_text,(window_dim[0]/2-large_font.size("My Decks")[0]/2,25))
            screen.blit(create_deck_text.text,create_deck_text.position)
            screen.blit(delete_deck_text.text,delete_deck_text.position)
            if deck_offset != 0:
                screen.blit(cards_sidebar_up,deck_up)
            if not len(deck_presets)-5*deck_offset < 5:
                screen.blit(cards_sidebar_down,deck_down)
            if deck_presets != []:
                for i in range(len(deck_presets)-5*deck_offset):
                    deck_presets[i+5*deck_offset].display()
        else:
            screen.blit(deck_inspects_to_presets_text.text,deck_inspects_to_presets_text.position)
            if chosen_deck != selected_deck and selected_deck.usable:
                screen.blit(select_deck_text.text,select_deck_text.position)
            elif chosen_deck != selected_deck and not selected_deck.usable:
                screen.blit(deck_unusable_text,(window_dim[0]-mjgs.size("Use deck")[0]-100,750))
            else:
                screen.blit(deck_selected_text,(window_dim[0]-mjgs.size("Deck selected")[0]-100,750))
            selected_deck.display() #actually displaying the deck is in DeckPreset.display()
            draw.circle(screen,M_BLUE,(cards_sidebar_rect.x+35,cards_sidebar_rect.y+35),40)
            screen.blit(cards_sidebar_button,(cards_sidebar_rect.x,cards_sidebar_rect.y))
            if cards_sidebar:
                draw.rect(screen,(90,180,30),Rect(window_dim[0]/2,115,window_dim[0]/2-20,window_dim[1]-225))
                if cards_sidebar_page == 0:
                    draw.circle(screen,(128,128,128),(cards_sidebar_up_rect.x+35,cards_sidebar_up_rect.y+35),40)
                else:
                    draw.circle(screen,M_BLUE,(cards_sidebar_up_rect.x+35,cards_sidebar_up_rect.y+35),40)
                screen.blit(cards_sidebar_up,(cards_sidebar_up_rect.x,cards_sidebar_up_rect.y))
                if cards_sidebar_page == len(all_cut)-1:
                    draw.circle(screen,(128,128,128),(cards_sidebar_down_rect.x+35,cards_sidebar_down_rect.y+35),40)
                else:
                    draw.circle(screen,M_BLUE,(cards_sidebar_down_rect.x+35,cards_sidebar_down_rect.y+35),40)
                screen.blit(cards_sidebar_down,(cards_sidebar_down_rect.x,cards_sidebar_down_rect.y))
                screen.blit(mjgs.render(f"{cards_sidebar_page+1}/{len(all_cut)}",True,(0,0,0)),(cards_sidebar_down_rect.x,cards_sidebar_down_rect.y-mjgs.get_height()/2-18))
                temp=False
                for i in range(len(all_cut[cards_sidebar_page])):
                    screen.blit(all_cut[cards_sidebar_page][i],all_cut_rects[cards_sidebar_page][i])
                    if all_cut_rects[cards_sidebar_page][i].collidepoint(mouse.get_pos()):
                        target=all_cut_rects[cards_sidebar_page][i]
                        target_tile=list(d_tiles.values())[cards_sidebar_page*9+i]
                        inforect=Rect(target.x+10,target.y+cut_dim[1]/2+5,cut_dim[0]-20,70)
                        addrect=Rect(target.x+10,target.y+5,cut_dim[0]-20,70)
                        draw.rect(screen,(15,180,220),inforect)
                        if target_tile.name not in list(selected_deck.original_mobs.keys())+list(selected_deck.original_items.keys()) and ((target_tile.border == "pink" and ((target_tile.kind == "Mob" and selected_deck.pink_mob == False) or (target_tile.kind == "Item" and selected_deck.pink_item == False))) or target_tile.border == "blue"):
                            draw.rect(screen,(0,200,0),addrect)
                        else:
                            draw.rect(screen,(128,128,128),addrect)
                        screen.blit(mjgs.render("Info",True,(255,255,255)),(target.x+45,target.y+cut_dim[1]/2+20))
                        screen.blit(mjgs.render("Add",True,(255,255,255)),(target.x+50,target.y+20))
                        move_hovering_over=(inforect,target_tile.full_sprite,addrect,cards_sidebar_page,i)
                        temp=True
                if not temp:
                    move_hovering_over=None
            temp=False
            if not cards_sidebar:
                for mob in selected_deck.mobs:
                    if mob.rect.collidepoint(mouse.get_pos()):
                        selected=mob
                        selected_deck.set_renders(mob.rect)
                        temp=True
                for item in selected_deck.items:
                    if item.rect.collidepoint(mouse.get_pos()):
                        selected=item
                        selected_deck.set_renders(item.rect)
                        temp=True
            if not temp:
                selected_deck.set_renders(None)
                selected=None

    elif state == "pregame":
        markers["do not connect"]=False
        screen.blit(pregame_text,(window_dim[0]/2-mjgs.size("Loading...")[0]/2,window_dim[1]/2))
        if player2name != None:
            print(f"{'\033[96m'}Opp. name: {player2name}{'\033[0m'}")
            player2=Player("Player 2",2,hand_anchors[1],[(x_rails[0],y_rails[0]),(x_rails[1],y_rails[0]),(x_rails[2],y_rails[0])])
            selected=None
            state="game"
        if not markers["name sent"]:
            write_buffer.append("n"+playername+"END")
            markers["name sent"]=True

    elif state == "game" or state in game_overs:
        if markers["deck built"] == False:
            decklist_p1={"mobs":{eval(mob):chosen_deck.original_mobs[mob] for mob in chosen_deck.original_mobs},"items":{eval(item):chosen_deck.original_items[item] for item in chosen_deck.original_items}}
            deck_p1 = {"mobs":deckbuilder(decklist_p1["mobs"]),"items":deckbuilder(decklist_p1["items"])}
            deck_p2 = {"mobs":deckbuilder(decklist_p2["mobs"]),"items":deckbuilder(decklist_p2["items"])}
            turn = 1
            draw_card(player2,deck_p2["mobs"],8)
            if markers["do not connect"]:
                for i in range(3):
                    player2.add_to_field("self",i,i,True)
            draw_card(player1,deck_p1["mobs"],8)
            markers["deck built"]=True
        if not markers["start of turn called"] and turn != 1:
            player1.souls += turn
            player2.souls += turn
            draw_card(player1,deck_p1["items"],drawing_cards)
            draw_card(player2,deck_p2["items"],drawing_cards)
            start_of_turn()
            markers["start of turn called"]=True
        if turn == 1:
            player1.souls = 10
        screen.blit(deck_plc.current_sprite,(deck_plc.rect.x,deck_plc.rect.y))
        screen.blit(whole_field.current_sprite,(fields_anchor[0],fields_anchor[1]))
        if setup == True or abs_subturn > 2:
            screen.blit(subturn_sprites[0],subturn_indic_pos)
        else:
            screen.blit(subturn_sprites[abs_subturn+1],subturn_indic_pos)
        for i in range(3):
            if player1.field[i] == None and type(selected) != Item and selected in player1.hand:
                temp=Rect(player1.field_pos[i],cut_dim)
                draw.rect(screen,ORANGE,temp,5)
                draw.rect(screen,(255,255,255),Rect(temp.centerx-20,temp.centery-5,40,10))
                draw.rect(screen,(255,255,255),Rect(temp.centerx-5,temp.centery-20,10,40))
        if postsubturn >= 2:
            skippost=True
            if postsubturn < 5 and player1.field[postsubturn-2] != None:
                if "end of turn" in player1.field[postsubturn-2].passives:
                    player1.field[postsubturn-2].passives["end of turn"](origin=player1.field[postsubturn-2],player=player1,loc=(player1.field[postsubturn-2].rect.x,player1.field[postsubturn-2].rect.y))
                    skippost=False
                if "end of turn" in player1.field[postsubturn-2].items:
                    for subitem in player1.field[postsubturn-2].items["end of turn"]:
                        subitem.effect(origin=player1.field[postsubturn-2],player=player1,item=subitem)
                    skippost=False
            if skippost:
                postsubturn += 1
        hand_cost=[]
        for card in player1.hand:
            if type(card) == Mob:
                hand_cost.append(card.cost)
            else:
                hand_cost.append(99)
        if setup == True and min(hand_cost) >= player1.souls:
            abs_subturn += 1
        if postsubturn >= 5 and setup == False:
            subturn = 1
            abs_subturn = 0
            postsubturn = 1
            turn += 1
            markers["start of turn called"] = False
            for card in player1.field:
                if card != None and card.status["aquatised"] > 0:
                    card.status["aquatised"] -= 1
            for card in player2.field:
                if card != None and card.status["aquatised"] > 0:
                    card.status["aquatised"] -= 1
        if abs_subturn >= 4 and setup == True:
            setup=False
            subturn=1
            abs_subturn=0
            player1.souls=1
            player2.souls=1
            draw_card(player1,deck_p1["items"],drawing_cards)
            draw_card(player2,deck_p2["items"],drawing_cards)
        filled_positions={}
        for i in range(len(player1.field)):
            if player1.field[i] != None:
                filled_positions[i] = player1.field[i]
        if len(filled_positions) > 0:
            subturn=list(filled_positions.keys())[abs_subturn%len(filled_positions)]+1
        if postsubturn == 1:
            draw.rect(screen,(255,255,255),Rect(player1.field_pos[subturn-1][0],player1.field_pos[subturn-1][1]+cut_dim[1]+10,cut_dim[0],10))
            if markers["start of move called"] == False and player1.field[subturn-1] != None and "on this turn" in player1.field[subturn-1].passives:
                player1.field[subturn-1].passives["on this turn"](player=player1,origin=player1.field[subturn-1],loc=(player1.field[subturn-1].rect.x,player1.field[subturn-1].rect.y))
                markers["start of move called"]=True
        else:
            draw.rect(screen,(255,255,255),Rect(player1.field_pos[postsubturn-2][0],player1.field_pos[postsubturn-2][1]+cut_dim[1]+10,cut_dim[0],10))
        player1.update()
        player2.update()
        if selected != None and not hide_large:
            if large_hideable:
                temp=Surface((window_dim[0],window_dim[1]),SRCALPHA,32)
                temp.fill((0,0,0,128))
                screen.blit(temp,(0,0))
            large_image=transform.scale(image.load(selected.original_sprite),(card_dim[0]*3,card_dim[1]*3)).convert()
            draw.rect(screen,ORANGE,Rect(selected.rect.x-5,selected.rect.y-5,selected.rect.width+10,selected.rect.height+10),5)
            screen.blit(large_image,large_image_pos)
        if type(selected) == Mob and selected == player1.field[subturn-1] and setup == False and not hide_large:
            if not attack_progressing:
                for position in selected.move_positions:
                    if position.collidepoint(mouse.get_pos()):
                        draw.rect(screen,ORANGE,position,5)
                        if selected.move_positions.index(position) < len(selected.moveset):
                            move_hovering_over=(position,selected.moveset[selected.move_positions.index(position)])
                        else:
                            move_hovering_over=(position,selected.abilities[selected.move_positions.index(position)-len(selected.moveset)])
            else:
                draw.rect(screen,ORANGE,move_hovering_over[0],5)
        elif type(selected) == Item and not setup and not hide_large:
            if selected.display_rect.collidepoint(mouse.get_pos()) and not attack_progressing:
                if not True in [card.rect.collidepoint(mouse.get_pos()) for card in player1.hand]:
                    draw.rect(screen,ORANGE,Rect(selected.display_rect.left-5,selected.display_rect.top-5,selected.display_rect.width,selected.display_rect.height),5)
                    move_hovering_over=(selected.display_rect,selected.effect)
            elif attack_progressing:
                draw.rect(screen,ORANGE,Rect(selected.display_rect.left-5,selected.display_rect.top-5,selected.display_rect.width,selected.display_rect.height),5)
        for card in targets:
            if card != None:
                temp=Rect(card.rect.x,card.rect.y,card.rect.width,card.rect.height)
                draw.rect(screen,ORANGE,temp,5)
                draw.rect(screen,(255,255,255),Rect(temp.centerx-20,temp.centery-5,40,10))
                draw.rect(screen,(255,255,255),Rect(temp.centerx-5,temp.centery-20,10,40))

        if markers["finishable"] and setup == False and not markers["game over called"]:
            if (player1.field == [None, None, None] and markers["concede"] == None) or markers["concede"] == "you":
                state = "lose"
                markers["freeze"]=True
                markers["fade"]=[60,[0,0,0],255,0,0] #duration in frames, final colour, final transparency, current transparency, transparency change per frame
                markers["game over called"]=True
                markers["fade"][4]=markers["fade"][2]/markers["fade"][0]
            if (player2.field == [None, None, None] and markers["concede"] == None) or markers["concede"] == "opp":
                state = "win"
                markers["freeze"]=True
                markers["fade"]=[60,[10,140,50],255,0,0]
                markers["fade"][4]=markers["fade"][2]/markers["fade"][0]
                markers["game over called"]=True
            if player1.field == [None, None, None] and player2.field == [None, None, None] and markers["concede"] == None:
                state ="tie"
                markers["freeze"]=True
                markers["fade"]=[60,[10,220,70],255,0,0]
                markers["fade"][4]=markers["fade"][2]/markers["fade"][0]
                markers["game over called"]=True
        screen.blit(mjgs.render(f"Abs:{str(abs_subturn)}, Sub:{str(subturn)}",True,(255,255,255)),(0,0))

    if state in game_overs:
        if not markers["sock closed"] and not markers["do not connect"]:
            sock.close()
            sock=''
            markers["sock closed"]=True
        colourval = markers["fade"][1]+[markers["fade"][3]]
        temps=Surface(window_dim).convert_alpha()
        temps.set_alpha(markers["fade"][3])
        temps.fill(markers["fade"][1])
        screen.blit(temps,(0,0))
        markers["await p2"]=False
        ai_wait_until=0
    if setup == False:
        if state == "lose":
            if markers["fade"][0] <= 0:
                if markers["you timeout"]:
                    screen.blit(you_timeout_text,(window_dim[0]/2-you_timeout_text.get_width()/2,window_dim[1]/2-100))
                elif markers["concede"] == "you":
                    screen.blit(you_conc_text,(window_dim[0]/2-large_font.size("You conceded")[0]/2,window_dim[1]/2-100))
                else:
                    screen.blit(lose_text,(window_dim[0]/2-large_font.size("You lost...")[0]/2,window_dim[1]/2-100))
                screen.blit(skill_issue_text,(window_dim[0]/2-small_font.size("skill issue")[0]/2,window_dim[1]/2))
                screen.blit(to_menu_text.text, to_menu_text.position)
            else:
                markers["fade"][0]-=1
                markers["fade"][3]+=markers["fade"][4]

        if state == "win":
            if markers["fade"][0] <= 0:
                if disconnect_cd <= 0:
                    screen.blit(opp_timeout_text,(window_dim[0]/2-opp_timeout_text.get_width()/2,window_dim[1]/2-100))
                elif markers["concede"] == "opp":
                    screen.blit(opp_conc_text,(window_dim[0]/2-large_font.size("Opponent conceded")[0]/2,window_dim[1]/2-100))
                else:
                    screen.blit(win_text,(window_dim[0]/2-large_font.size("You won!")[0]/2,window_dim[1]/2-100))
                screen.blit(to_menu_text.text, to_menu_text.position)
            else:
                markers["fade"][0]-=1
                markers["fade"][3]+=markers["fade"][4]

        if state == "tie":
            if markers["fade"][0] <= 0:
                screen.blit(tie_text,(window_dim[0]/2-large_font.size("You tied!")[0]/2,window_dim[1]/2-100))
                screen.blit(to_menu_text.text, to_menu_text.position)
            else:
                markers["fade"][0]-=1
                markers["fade"][3]+=markers["fade"][4]

    fps_text=mjgs.render(f"FPS:{str(round(clock.get_fps(),2))}",True,(255,255,255))
    screen.blit(fps_text,(0,fps_text.get_height()))
    cursor_coord=small_font.render("-"+str(mouse.get_pos()),True,(0,0,0))
    if coord_tooltip:
        draw.rect(screen,(255,255,255),Rect((mouse.get_pos()),(cursor_coord.get_width(),20)))
        screen.blit((cursor_coord),(mouse.get_pos()))
    for info in linger_anims:
        if info[2]+1-info[3] == 0:
            linger_anims.pop(linger_anims.index(info))
            break
        else:
            linger_anims[linger_anims.index(info)]=(info[0],info[1],info[2]+1,info[3],info[4],info[5])
            info=(info[0],info[1],info[2]+1,info[3],info[4],info[5])
        if info[4] == "inverse up":
            screen.blit(info[0],(info[1][0],info[1][1]+info[5]/info[2]))
        elif info[4] == "inverse down":
            screen.blit(info[0],(info[1][0],info[1][1]-info[5]/info[2]))
    if state == "settings":
        screen.blit(settings_text,(window_dim[0]/2-settings_text.get_width()/2,10))
        screen.blit(settings_back_text.text,settings_back_text.position)
        if last_screen == "game":
            screen.blit(conc_text.text,conc_text.position)
        elif last_screen == "menu":
            if subsetting == None:
                screen.blit(to_profile_text.text,to_profile_text.position)
                screen.blit(to_bg_cstm_text.text,to_bg_cstm_text.position)
                screen.blit(cardbg_change_text.text,cardbg_change_text.position)
                screen.blit(change_game_layout_text.text,change_game_layout_text.position)
                screen.blit(uninstall_text.text,uninstall_text.position)
            elif subsetting == "profile":
                screen.blit(name_change_text.text,name_change_text.position)
                screen.blit(playername_text,(250,150))
                if name_changing:
                    draw.rect(screen,(255,255,255),Rect(window_dim[0]/2,200,window_dim[0]/2-50,60))
                    screen.blit(mjgs.render(playername,True,(0,0,0)),(window_dim[0]/2+10,210))
            elif subsetting == "cardbg":
                for bg in card_bgs:
                    bg.display()
            elif subsetting == "layout":
                for layout in layouts:
                    layout.display()
            elif subsetting == "uninstall":
                if not markers["uninstalling"]:
                    screen.blit(uninstall_warn_text_1,(window_dim[0]/2-uninstall_warn_text_1.get_width()/2,200))
                    screen.blit(uninstall_warn_text_2,(window_dim[0]/2-uninstall_warn_text_2.get_width()/2,300))
                    screen.blit(uninstall_warn_text_3,(window_dim[0]/2-uninstall_warn_text_3.get_width()/2,400))
                    screen.blit(uninstall_cancel_text.text,uninstall_cancel_text.position)
                    screen.blit(uninstall_confirm_text.text,uninstall_confirm_text.position)
                else:
                    screen.blit(uninstalling_text,(window_dim[0]/2-uninstalling_text.get_width()/2,window_dim[1]/2))
    if selected_deck == None:
        screen.blit(settings_button[0],settings_button[1])
    if markers["disconnecting"]:
        disconnect_cd -= 1
    else:
        disconnect_cd=600
    if disconnect_cd <= 0:
        state="win"
        setup=False
        markers["concede"]="opp"
        if type(sock) == socket.socket:
            try:
                sock.send("tEND".encode())
                print(f"{'\033[93m'}Concede indicated by timeout{'\033[0m'}")
            except:
                pass
    if tm.time() >= ai_wait_until and markers["await p2"] and markers["do not connect"]:
        temp, p2_progress_turn=execute(p2_move(player2.hand,player2.field,player2.souls))
        if type(temp) == bool:
            markers["await p2"]=temp
    if markers["await p2"]:
        thinking_progress+=4
        thinking_rot=transform.rotate(thinking,thinking_progress)
        if state != "settings":
            screen.blit(thinking_rot,thinking_rot.get_rect(center=(870,75)))
    else:
        thinking_progress=0
    display.update()
    clock.tick(FPS)

    '''
    To-do:
    1. Does item application count as a subturn?
    2. Get item stealing to work
    3. HOLD: Implement setting colour for decks
    4. Add auto-updater feature
    5. Postsubturns for player 2

    Bugs:
    '''