from __future__ import annotations
from pygame import *
from collections.abc import Callable
from typing import Literal
import random as r
import time as t
import socket
import select
from math import copysign

type Card = Mob|Item
type Coord = tuple[int|float,int|float]
type Size = tuple[int,int]
type Path = str
type Attack_params = dict[Literal["origin"]:Card,Literal["target"]:Card,Literal["damage"]:int,Literal["noattack"]:bool]
#Name:LAPTOP-20C14P7N, Address:172.20.57.66
#None values mean add later

window_dim=(1500,850)
screen=display.set_mode(window_dim)

class Mob(sprite.Sprite):
    def __init__(self,name:str,cost:int,health:int,abilities:list[Ability],attacks:list[Callable],passives:dict[Literal["end of turn","start of turn","on death","on hurt","on attack","when played","on this turn","always","end this turn"],Callable],items:dict[Literal["end of turn","start of turn","on death","on hurt","on attack","when played","on this turn"],Item],mob_class:Literal["undead","arthropod","aquatic","human","misc"],biome:Literal["plains","cavern","ocean","swamp"],border:Literal["blue","pink"],sprite:Path,init_pos:Coord,cut_sprite:Path,move_positions:list[tuple[int,int,int,int]],**kwargs):
        super().__init__()
        #MOB INFO
        self.name=name
        self.cost=cost
        self.health=health
        self.max_health=health
        self.original_health=health
        #passives listed first on card, then attacks, then abilities
        self.abilities=abilities 
        self.passives=passives #dict, index is a trigger marker which allows functions to know when to call it, same for items
        self.moveset=attacks #used for finding which one was clicked
        self.move_positions=[]
        for position in move_positions:
            self.move_positions.append(Rect(position[0],position[1],position[2]-position[0],position[3]-position[1]))#hitboxes of moves, in order
        self.items=items
        self.mob_class=mob_class
        self.biome=biome
        self.status={"psn":0,"aquatised":0}
        self.border=border #blue or pink
        self.miscs=kwargs
        self.original_miscs=kwargs
        self.proxy_for=None
        self.proxy=None
        #SPRITE AND COORDS
        self.front_sprite=transform.scale(image.load(sprite),card_dim).convert()
        self.original_sprite=sprite
        self.cut_sprite=transform.scale(image.load(cut_sprite),cut_dim).convert()
        self.back_sprite=transform.scale(image.load(cardback),card_dim).convert()
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
        global setup
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
            if selected == self and position.collidepoint(mouse.get_pos()) and not attack_progressing and self == player1.field[subturn-1] and setup == False:
                draw.rect(screen,ORANGE,position,5)
                if self.move_positions.index(position) < len(self.moveset):
                    move_hovering_over=(position,self.moveset[self.move_positions.index(position)])
                else:
                    move_hovering_over=(position,self.abilities[self.move_positions.index(position)-len(self.moveset)])
        if attack_progressing:
            draw.rect(screen,ORANGE,move_hovering_over[0],5)
        screen.blit(self.current_sprite, (self.rect.x,self.rect.y))
        for item in self.items:
            if len(self.items) <= 2:
                self.items[item].rect.x, self.items[item].rect.y= (self.rect.x+cut_dim[0]*2/3, self.rect.y+item_dim[1]*list(self.items.keys()).index(item))
            self.items[item].update()

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
        return self

class Item(sprite.Sprite):
    def __init__(self,name:str,cost:int,effect:Callable,sprite:Path,init_pos:Coord,cut_sprite:Path,border:Literal["blue","pink"],dimensions:Size,condition:Literal["end of turn","start of turn","on death","on hurt","on attack","when played"],uses:int,targets:Literal["can be healed","player1 field","player2 field","whole field","all on field","all healable"]):
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
        #SPRITE AND COORDS
        self.front_sprite=transform.scale(image.load(sprite),dimensions).convert_alpha()
        self.original_sprite=sprite
        self.cut_sprite=transform.scale(image.load(cut_sprite),item_dim).convert()
        self.back_sprite=transform.scale(image.load(cardback),card_dim).convert()
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

    def find_targets(self):
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
        return tempt

class Player():
    def __init__(self,name:str,player_number:int,hand_pos:Coord,field_pos:list[Coord]):
        self.name=name
        self.player_number=player_number
        self.hand=[]
        self.field: list[None|Mob]=[None,None,None]
        self.souls=20
        self.hand_pos=hand_pos
        self.field_pos=field_pos
        self.soul_colour=list(SOUL_COLOUR)
        if player_number == 1:
            self.souls_pos=(field_pos[2][0]+cut_dim[0]+10,window_dim[1]-token_dim[1]-card_dim[1])
        elif player_number == 2:
            self.souls_pos=(field_pos[2][0]+cut_dim[0]+10,50)

    def update(self):
        global abs_subturn
        for i in range(len(self.hand)):
            if self.player_number==2:
                self.hand[i].switch_sprite("back")
            self.hand[i].rect.y, self.hand[i].rect.x= (self.hand_pos[1],self.hand_pos[0]+card_dim[0]*i)
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
                        result=card.passives["on death"](origin=card,player=self)
                    if "on death" in card.items:
                        result=card.items["on death"](origin=card,player=self)
                    if result == None:
                        if card.proxy_for != None:
                            card.proxy_for.proxy=None
                        self.field[self.field.index(card)]=None
                        if self.player_number == 1:
                            abs_subturn -= 1
                if "always" in card.passives:
                    card.passives["always"](origin=card,player=self)
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

    def add_to_field(self,card:int,pos:int,ignore_cost:bool=False,card_override=None,pos_override=None): #card is index number of hand card to take, pos is field position to take (in human number terms, not list index)
        if card_override == None:
            target=self.hand.pop(card)
        else:
            target=card_override
        if type(target) == Mob:
            self.field[pos-1]=target
            target.switch_sprite("cut")
            target.rect.x, target.rect.y=self.field_pos[pos-1]
            if not ignore_cost:
                self.souls -= target.cost
        elif type(target) == Item:
            if target.condition != "when played":
                self.field[pos-1].items[target.condition]=target
                target.switch_sprite("cut")
                if not ignore_cost:
                    self.souls -= target.cost
            else:
                if pos_override == None:
                    target.effect(target=self.field[pos-1], origin=target, player=self)
                else:
                    target.effect(target=pos_override, origin=target, player=self)

    def reset(self):
        self.hand=[]
        self.field=[None, None, None]
        self.souls=20

class ClickableText():
    def __init__(self,font,text:str,colour:tuple[int,int,int],position:Coord):
        self.text=font.render(text,True,colour)
        self.textrect=self.text.get_rect()
        self.position=position
        self.textrect.x=position[0]
        self.textrect.y=position[1]

class Ability():
    def __init__(self,cost:int,effect:Callable,targets:str):
        self.cost=cost
        self.effect=effect
        self.targets=targets

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

def nofunction_item(**kwargs):
    pass

def deckbuilder(list_to_use:dict[Card,int]) -> list[Card]:
    here_deck=[]
    for card in list_to_use:
        for i in range(list_to_use[card]):
            actual_card=eval(card)
            here_deck.append(actual_card)
    r.shuffle(here_deck)
    return here_deck

def atk_check(func) -> bool: #decorator that applies to all attacks, first decorator layer
    def atk_wrapper(**kwargs):
        global markers
        if kwargs["noattack"] == False and "Egg Rain" not in [item.name for item in list(kwargs["origin"].items.values())]: #egg rain
            result:list[bool,int,list[Card]]=list(func(**kwargs))
            if markers["forage"] > 1: #forage
                markers["forage"] -= 1
            elif markers["forage"] == 1:
                result[1] += 1
                markers["forage"]=False
            if len(result) == 2:
                result.append([kwargs["target"]])
            for card in result[2]:
                if "on attack" in kwargs["origin"].items:
                    result=kwargs["origin"].items["on attack"].effect(origin=kwargs["origin"],target=card,player=player1,original=result)
                if card.proxy != None:
                    card=card.proxy
                card.health-=result[1]
                if kwargs["origin"] in player2.field: #quick strike
                    for mob in [mob for mob in player1.field if (mob != None and mob.name == "Horse")]:
                        if kwargs["origin"].proxy == None:
                            kwargs["origin"].health-=1
                        else:
                            kwargs["origin"].proxy.health-=1
                        if "on hurt" in kwargs["origin"].passives:
                            kwargs["origin"].passives["on hurt"](origin=mob,target=card,damage=1)
                        if "on hurt" in kwargs["origin"].items:
                            kwargs["origin"].items["on hurt"].effect(origin=mob,target=card,player=kwargs["player"],damage=1)
                            kwargs["origin"].items["on hurt"].uses-=1
                            if kwargs["origin"].items["on hurt"].uses == 0:
                                del kwargs["origin"].items["on hurt"]
                if "on hurt" in card.passives and result[1] != 0:
                    card.passives["on hurt"](origin=kwargs["origin"],target=card,player=kwargs["player"],damage=result[1])
                if "on hurt" in card.items and result[1] != 0:
                    card.items["on hurt"].effect(origin=kwargs["origin"],target=card,player=kwargs["player"],damage=result[1])
                    card.items["on hurt"].uses-=1
                    if card.items["on hurt"].uses == 0:
                        del card.items["on hurt"]
            if "on attack" in kwargs["origin"].items:
                kwargs["origin"].items["on attack"].uses -= 1
                if kwargs["origin"].items["on attack"].uses == 0:
                    del kwargs["origin"].items["on attack"]
            return result[0]
        else:
            return func(origin=kwargs["origin"],target=kwargs["target"],player=kwargs["player"],noattack=True)[0]
    return atk_wrapper

def psv_check(func): #decorator that applies to all passives, first decorator layer
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
            #print(f"{func.__name__} used.")
        return result
    return psv_wrapper

def abl_check(func):  #decorator that applies to all abilities, first decorator layer
    def abl_wrapper(**kwargs):
        if kwargs["player"].player_number == 1:
            opp=player2
        else:
            opp=player1
        match=opp.field[kwargs["player"].field.index(kwargs["origin"])]
        if "Egg Rain" in [item.name for item in list(kwargs["origin"].items.values())] or (match != None and match.name == "Frog"): #egg rain and tongue snare
            result=None
        else:
            result=func(**kwargs)
        return result
    return abl_wrapper

def itm_check(func): #decorator that applies to all items, first decorator layer
    def itm_wrapper(**kwargs):
        result=None
        targets:list=func(origin=kwargs["origin"],target=kwargs["target"],player=kwargs["player"],only_targeting=True)
        for card in targets:
            if card != None and card.name != "Sunken": #porous body
                if card == None:
                    result=func(**kwargs)
                else:
                    result=func(origin=kwargs["origin"],target=card,player=kwargs["player"],original=kwargs["original"])
        return result
    return itm_wrapper

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
def child_support_avoider(**kwargs): #passive: always
    if kwargs["player"].player_number == 1:
        opp=player2
    else:
        opp=player1
    if len([mob for mob in opp.field if mob != None]) == 1 and setup == False:
        kwargs["origin"].health=0

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

@psv_check
def elders_curse(**kwargs): #passive: end of turn
    global selected
    global selected_move
    global attack_progressing
    global move_hovering_over
    global targets
    if kwargs["player"] == player1 and kwargs["origin"] in player1.field:
        selected=kwargs["origin"]
        selected_move=kwargs["origin"].moveset[0]
        attack_progressing=True
        move_hovering_over=(kwargs["origin"].move_positions[0],kwargs["origin"].moveset[0])
        targets=player2.field

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
def forage(**kwargs): #passive: on this turn
    global markers
    markers["forage"]=3

@itm_check
def goat_horn_bounce(**kwargs): #item
    if "only_targeting" not in kwargs:
        player2.hand.append(kwargs["target"].reset())
        player2.field[player2.field.index(kwargs["target"])]=None
        kwargs["target"].switch_sprite("back")
    else:
        return [kwargs["target"]]

@psv_check
def infinity(**kwargs): #passive: on hurt
    kwargs["target"].health+=kwargs["damage"]-1

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
        for i in range(2):
            kwargs["player"].hand.append(deck.pop())
    else:
        return [None]

@itm_check
def milk_cleanse(**kwargs): #item
    if "only_targeting" not in kwargs:
        kwargs["target"].items={}
    else:
        return [kwargs["target"]]

@abl_check
def milk_share(**kwargs) -> bool: #ability
    result=False
    if kwargs["player"].souls >= 1:
        result=True
        for card in kwargs["player"].field:
            if card != None and card != kwargs["origin"]:
                card.heal(1)
        kwargs["player"].souls -= 1
    return result

@abl_check
def monkey(**kwargs):
    global markers
    markers["monkey"]=60

@psv_check
def mystery_egg(**kwargs): #passive: on this turn
    kwargs["player"].hand.append(deck.pop())

@abl_check
def nah_id_win(**kwargs): #ability
    if kwargs["player"].player_number == 1:
        opp=player2
    else:
        opp=player1
    opp.souls -= 3

@psv_check
def play_dead(**kwargs): #passive: on death
    kwargs["origin"].switch_sprite("front")
    kwargs["player"].hand.append(kwargs["origin"])

@abl_check
def prime(**kwargs): #ability
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
        kwargs["origin"].rect.x, kwargs["origin"].rect.y=tempc
    elif kwargs["origin"].miscs["prime_status"] == 1:
        for card in opp.field:
            if card != None:
                card.health -= 3
                if "on hurt" in card.passives:
                    card.passives["on hurt"](origin=kwargs["origin"],target=card,damage=3)
        kwargs["origin"].health=0

@itm_check
def puffer_poison(**kwargs): #item
    if "only_targeting" not in kwargs:
        kwargs["target"].status["psn"] += 1
    else:
        return [card for card in player2.field if card != None]

@atk_check
def purple(**kwargs:Attack_params) -> tuple[Literal[False],int,list[Card]]: #attack
    dmg=0
    if kwargs["noattack"] == False:
        dmg=3
    return False, dmg, [card for card in player1.field+player2.field if card != None]

@atk_check
def rush(**kwargs:Attack_params) -> tuple[Literal[True],int]: #attack
    dmg=0
    if kwargs["noattack"] == False:
        dmg=1
    return True, dmg

@psv_check
def self_aid(**kwargs): #passive: end this turn
    kwargs["origin"].heal(1)

@itm_check
def shield_protect(**kwargs): #item
    if "only_targeting" not in kwargs:
        kwargs["target"].health+=kwargs["damage"]
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
def split(**kwargs) -> None|Literal["cancel"]: #passive: on death
    if kwargs["origin"].miscs["rotation"] == 0:
        kwargs["origin"].health=2
        kwargs["origin"].max_health=2
        kwargs["origin"].cut_sprite=transform.rotate(kwargs["origin"].cut_sprite,-90.0)
        tempc=(kwargs["origin"].rect.x,kwargs["origin"].rect.y)
        kwargs["origin"].switch_sprite("cut")
        kwargs["origin"].rect.x, kwargs["origin"].rect.y=tempc
        kwargs["origin"].miscs["rotation"]=1
        return "cancel"
    else:
        return None

@psv_check
def spore(**kwargs): #passive: on death
    opp=None
    if kwargs["player"].player_number == 1:
        opp=player2
    else:
        opp=player1
    for card in opp.field:
        if card != None:
            card.status["psn"] += 1

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
def thorn_body(**kwargs): #passive: on hurt
    kwargs["origin"].health-=1

@atk_check
def tongue_whip(**kwargs) -> tuple[Literal[True],int]: #attack
    global until_end
    global selected
    global targets
    global markers
    dmg=0
    if kwargs["noattack"] == False:
        dmg=1
        if kwargs["target"].items == {}:
            pass
        elif len(kwargs["target"].items) == 1:
            kwargs["origin"].items[list(kwargs["target"].items.keys())[0]]=list(kwargs["target"].items.values())[0]
            del kwargs["target"].items[list(kwargs["target"].items.keys())[0]]
        else:
            until_end += 3
            targets = kwargs["target"].items
            selected=kwargs["origin"]
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
def undead(**kwargs): #passive: on hurt
    if kwargs["origin"].health == kwargs["origin"].max_health and kwargs["damage"] >= kwargs["origin"].health:
        kwargs["origin"].health=1

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

@abl_check
def witch_healing(**kwargs): #ability
    global until_end
    if kwargs["origin"].miscs["heal_count"] == 1:
        until_end=0
        kwargs["origin"].miscs["heal_count"]=0
    elif kwargs["origin"].miscs["heal_count"] == 0:
        until_end=1
        kwargs["origin"].miscs["heal_count"]=1
    kwargs["target"].heal(1)

@abl_check
def witch_poison(**kwargs): #ability
    global until_end
    if kwargs["origin"].miscs["poison_count"] == 1:
        kwargs["origin"].miscs["poison_count"]=0
        until_end=0
    elif kwargs["origin"].miscs["poison_count"] == 0:
        kwargs["origin"].miscs["poison_count"]=1
        until_end=1
    kwargs["target"].status["psn"]+=1

@abl_check
def wool_guard(**kwargs) -> Literal["break"]|None: #ability
    if kwargs["origin"] != kwargs["target"]:
        kwargs["origin"].proxy_for=kwargs["target"]
        kwargs["target"].proxy=kwargs["origin"]
        kwargs["origin"].rect.x=kwargs["target"].rect.x
        kwargs["origin"].rect.y=kwargs["target"].rect.y+copysign(40,1.5-kwargs["player"].player_number)
        if kwargs["origin"].proxy != None:
            kwargs["origin"].proxy.proxy_for=None
            kwargs["origin"].proxy.rect.x, kwargs["origin"].proxy.rect.y= player1.field_pos[player1.field.index(kwargs["origin"].proxy)]
            kwargs["origin"].proxy=None
        return "break"

def start_of_turn():
    for card in player1.field:
        if card != None and "start of turn" in card.passives:
            card.passives["start of turn"]()
        if card != None and "start of turn" in card.items:
            card.items["start of turn"].effect()
            card.items["start of turn"].uses -= 1
            if card.items["start of turn"].uses == 0:
                del card.items["start of turn"]
    for card in player2.field:
        if card != None and "start of turn" in card.passives:
            card.passives["start of turn"]()
        if card != None and "start of turn" in card.items:
            card.items["start of turn"].effect()
            card.items["start of turn"].uses -= 1
            if card.items["start of turn"].uses == 0:
                del card.items["start of turn"]

#constants
title_img=transform.scale(image.load("title.png"),(842,120)).convert_alpha()
card_dim=(150,225)
card_dim_rot=(225,150)
cut_dim=(169,172)
item_dim=(75,75)
token_dim=(30,30)
soul=transform.scale(image.load("soul.png"),token_dim).convert()
ORANGE = (255,180,0)
SOUL_COLOUR=(255,255,255)
starting_cards=5
drawing_cards=2
cardback="card_back.png"
background=transform.scale(image.load("background.png"),window_dim).convert()
FPS=60
clock=time.Clock()
fields_anchor=(90,40)
card_spacing_x=70
card_spacing_y=50
y_rails=[fields_anchor[1],fields_anchor[1]+card_spacing_y*2+card_dim_rot[1]+cut_dim[1]]
x_rails=[fields_anchor[0],fields_anchor[0]+cut_dim[0]+card_spacing_x,fields_anchor[0]+cut_dim[0]*2+card_spacing_x*2]
hearts_rails=[y_rails[0]+cut_dim[0]+10,y_rails[1]-10-20] #0: player 2, 1: player 1
game_overs=("win", "tie", "lose")
PORT=6543
effect_sprites={"psn":image.load("psn.png").convert_alpha(),"aquatised":transform.scale(image.load("aquatised.png"),(23,23)).convert()}
monkey_sprite=transform.scale(image.load("monkey.png"),(840*(window_dim[1]/859),window_dim[1])).convert_alpha()
subturn_sprites=[transform.scale(image.load("abs_subturn_none.png"),(150,360)).convert(),transform.scale(image.load("abs_subturn_1.webp"),(150,360)).convert(),transform.scale(image.load("abs_subturn_2.webp"),(150,360)).convert(),transform.scale(image.load("abs_subturn_3.png"),(150,360)).convert()]

#variables
running=True
state="menu"
connect_state="idle"
deck=[]
turn=0
setup=True
subturn=1 #subturn numbers start from 1, keeps track of which card should be attacking
abs_subturn=1 #keeps track of how many subturns have passed
abs_abs_subturn=1
postsubturn=1 #postsubturn numbers start from 2
attack_choosing_state=False
HOST=''
sock=''
markers={"retry":False, "deck built":False, "do not connect":True, "start of turn called":False, "not enough souls":[0,0,0,0], "data received, proceed":False, "just chose":False, "finishable":True, "freeze":False, "fade":[0,[0,0,0],0,0,0], "game over called":False,"start of move called":False,"item stealing":(False, None),"forage":False,"monkey":0,"until end just changed":False}
selected=None #card displayed on the side
selected_move=None #move that has been selected
attack_progressing=False #is it the attack target choosing stage
move_hovering_over=None #tuple of Rect of attack being hovered over and attack function itself, used for click detection
targets=[]
until_end=0
ability_selected=False

#define cards here
#Note: cards for deck use are defined by deckbuilder(), which takes these strings and eval()s them into objects
#This is so each deck entry has a separate memory value
deck_plc=Item("Deck Placeholder",0,None,"card_back_rot.png",(100,262),"card_back_rot.png",None,card_dim_rot,'',None,None)
whole_field=Item("THE ENTIRE FIELD!!!",0,nofunction_item,r"Sprites\Whole Field.png",(fields_anchor[0],fields_anchor[1]),r"Sprites\Whole Field.png","pink",(3*cut_dim[0]+3*card_spacing_x,2*cut_dim[1]+card_dim_rot[1]+2*card_spacing_y),None,None,None)
preset_dummy=Mob("Dummy",0,999,[],[bite],{},{},"misc","plains","pink",r"Sprites\Dummy.png",(0,0),r"Cut Sprites\Dummy.png",[(987,512,1323,579)])
axolotl=r'Mob("Axolotl",3,3,[],[bite],{"on death":play_dead},{},"aquatic","ocean","blue",r"Sprites\Axolotl.png",(0,0),r"Cut SPrites\Axolotl.png",[(987,512,1323,579)])'
bogged=r'Mob("Bogged",3,3,[],[snipe],{"on death":spore},{},"undead","swamp","blue",r"Sprites\Bogged.webp",(0,0),r"Cut Sprites\Bogged.jpg",[(987,522,1323,579)])'
bread=r'Item("Bread",1,bread_heal,r"Sprites\Bread.png",(0,0),r"Cut Sprites\Bread.png","blue",card_dim,"when played",1,"all healable")'
cake=r'Item("Cake",2,cake_heal,r"Sprites\Cake.png",(0,0),r"Cut Sprites\Cake.png","blue",card_dim,"when played",1,"player1 field")'
cow=r'Mob("Cow",3,4,[Ability(1,milk_share,"can be healed")],[rush],{},{},"misc","plains","blue",r"Sprites\Cow.png",(0,0),r"Cut Sprites\Cow.png",[(987,445,1323,502),(987,502,1323,569)])'
chicken=r'Mob("Chicken",1,2,[],[rush],{"on this turn":mystery_egg},{},"misc","plains","blue",r"Sprites\Chicken.png",(0,0),r"Cut Sprites\Chicken.png",[(987,512,1323,579)])'
creeper=r'Mob("Creeper",2,2,[Ability(0,prime,"player2 field")],[],{},{},"misc","cavern","blue",r"Sprites\Creeper.png",(0,0),r"Cut Sprites\Creeper.png",[(987,445,1323,552)],prime_status=0)'
drowned=r'Mob("Drowned",2,4,[],[drown],{},{},"aquatic","ocean","blue",r"Sprites\Drowned.png",(0,0),r"Cut Sprites\Drowned.png",[(987,497,1323,564)])'
dummy=r'Mob("Dummy",0,999,[],[bite],{},{},"misc","plains","pink",r"Sprites\Dummy.png",(0,0),r"Cut Sprites\Dummy.png",[(987,512,1323,579)])'
elder=r'Mob("Elder",6,6,[],[warding_laser],{"end of turn":elders_curse},{},"aquatic","ocean","pink",r"Sprites\Elder.png",(0,0),r"Cut Sprites\Elder.png",[(987,522,1323,589)])'
egg_rain=r'Item("Egg Rain",1,nofunction_item,r"Sprites\Egg Rain.png",(0,0),r"Cut Sprites\Egg Rain.png","blue",card_dim,"on attack",1,"player2 field")'
frog=r'Mob("Frog",2,3,[],[tongue_whip],{},{},"aquatic","swamp","blue",r"Sprites\Frog.png",(0,0),r"Cut Sprites\Frog.png",[(987,512,1323,579)])'
goat_horn=r'Item("Goat Horn",3,goat_horn_bounce,r"Sprites\Goat Horn.png",(0,0),r"Cut Sprites\Goat Horn.png","pink",card_dim,"when played",1,"special: goat horn")'
guardian=r'Mob("Guardian",4,3,[],[eye_laser],{"on hurt":thorn_body},{},"aquatic","ocean","blue",r"Sprites\Guardian.png",(0,0),r"Cut Sprites\Guardian.png",[(987,502,1323,569)])'
horse=r'Mob("Horse",4,5,[],[bite],{},{},"misc","plains","pink",r"Sprites\Horse.png",(0,0),r"Cut Sprites\Horse.png",[(987,512,1323,579)])'
loot_chest=r'Item("Loot Chest",0,loot_chest_draw,r"Sprites\Loot Chest.png",(0,0),r"Cut Sprites\Loot Chest.png","blue",card_dim,"when played",1,"whole field")'
milk=r'Item("Milk",2,milk_cleanse,r"Sprites\Milk.png",(0,0),r"Cut Sprites\Milk.png","blue",card_dim,"when played",1,"player1 field")'
muddy_pig=r'Mob("Muddy Pig",2,3,[],[rush],{"on this turn":forage},{},"misc","plains","blue",r"Sprites\Muddy Pig.png",(0,0),r"Cut Sprites\Muddy Pig.png",[(987,512,1323,579)])'
pufferfish=r'Item("Pufferfish",2,puffer_poison,r"Sprites\Pufferfish.png",(0,0),r"Cut Sprites\Pufferfish.png","blue",card_dim,"when played",1,"whole field")'
satoru_gojo=r'Mob("Satoru Gojo",9,20,[Ability(0,nah_id_win,"whole field")],[purple],{"on hurt":infinity},{},"misc","plains","pink",r"Sprites\Satoru Gojo.png",(0,0),r"Cut Sprites\Satoru Gojo.png",[(987,502,1323,554),(987,554,1323,614)])'
sheep=r'Mob("Sheep",3,4,[Ability(0,wool_guard,"can proxy")],[rush],{},{},"misc","plains","blue",r"Sprites\Sheep.png",(0,0),r"Cut Sprites\Sheep.png",[(987,447,1323,499),(987,499,1323,554)])'
shield=r'Item("shield",2,shield_protect,r"Sprites\Shield.png",(0,0),r"Cut Sprites\Shield.png","blue",card_dim,"on hurt",1,"player1 field")'
skeleton=r'Mob("Skeleton",2,3,[],[snipe],{"on hurt":undead},{},"undead","cavern","blue",r"Sprites\Skeleton.png",(0,0),r"Cut Sprites\Skeleton.png",[(987,512,1323,569)])'
slime=r'Mob("Slime",3,4,[],[squish],{"on death":split},{},"misc","swamp","blue",r"Sprites\Slime.png",(0,0),r"Cut Sprites\Slime.png",[(987,537,1323,609)],rotation=0)'
spider=r'Mob("Spider",1,2,[],[spider_bite],{},{},"arthropod","cavern","blue",r"Sprites\Spider.png",(0,0),r"Cut Sprites\Spider.png",[(987,512,1323,569)])'
sunken=r'Mob("Sunken",2,3,[],[snipe],{},{},"aquatic","ocean","blue",r"Sprites\Sunken.png",(0,0),r"Cut Sprites\Sunken.png",[(987,497,1323,554)])'
sword=r'Item("Sword",1,sword_slash,r"Sprites\Sword.png",(0,0),r"Cut Sprites\Sword.png","blue",card_dim,"on attack",1,"player1 field")'
toji=r'Mob("Toji",9,20,[Ability(0,monkey,"whole field")],[knife_thing],{"always":child_support_avoider},{},"undead","plains","pink",r"Sprites\Toji.png",(0,0),r"Cut Sprites\Toji.png",[(987,497,1323,554),(987,554,1323,614)])'
trident=r'Item("Trident",2,trident_stab,r"Sprites\Trident.png",(0,0),r"Cut SPrites\Trident.png","pink",card_dim,"on attack",1,"player1 field")'
witch=r'Mob("Witch",3,4,[Ability(1,witch_poison,"player2 field"),Ability(1,witch_healing,"player1 field")],[],{"end this turn":self_aid},{},["human"],"swamp","blue",r"Sprites\Witch.png",(0,0),r"Cut Sprites\Witch.png",[(987,497,1323,569),(987,569,1323,639)],poison_count=0,heal_count=0)'
zombie=r'Mob("Zombie",2,4,[],[bite],{"on hurt":undead},{},"undead","cavern","blue",r"Sprites\Zombie.png",(0,0),r"Cut Sprites\Zombie.png",[(987,512,1323,579)])'
#Mob()

decklist={frog:30}
#playername=input("Enter your name: ")
playername="J1"
player1=Player(playername,1,(fields_anchor[0],y_rails[1]+cut_dim[1]+card_spacing_y),[(x_rails[0],y_rails[1]),(x_rails[1],y_rails[1]),(x_rails[2],y_rails[1])])
player2:Player=''

display.set_caption("Minecards")

font.init()
mjgs=font.Font("mojangles.ttf",40)
small_font=font.Font("mojangles.ttf",20)
large_font=font.Font("mojangles.ttf",80)
beta_text=mjgs.render("Closed Beta",True,(255,100,0))
host_text=ClickableText(mjgs,"Create Game",(0,0,0),(window_dim[0]/2-mjgs.size("Create Game")[0]/2,550))
connect_text=ClickableText(mjgs,"Join Game",(0,0,0),(window_dim[0]/2-mjgs.size("Join Game")[0]/2,650))
connecting_text=mjgs.render("Waiting for connection",True,(255,0,0))
ip_enter_text=mjgs.render("Enter host IPv4",True,(0,0,0))
ip_submit_text=ClickableText(mjgs,"Connect",(0,0,0),(window_dim[0]/2-mjgs.size("Connect")[0]/2,750))
pregame_text=mjgs.render("Loading...",True,(0,0,0))
retry_text=mjgs.render("Retry Connection",True,(255,0,0))
game_plc_text=mjgs.render("Await further programming",True,(0,0,0))
win_text=large_font.render("You won!",True,(30,150,20))
lose_text=large_font.render("You lost...",True,(255,0,0))
skill_issue_text=small_font.render("skill issue",True,(255,255,255))
tie_text=large_font.render("You tied!",True,(255,255,0))
to_menu_text=ClickableText(mjgs,"Back to menu",(255,255,255),(window_dim[0]/2-mjgs.size("Back to menu")[0]/2,3*window_dim[1]/4))

while running:
    screen.blit(background,(0,0))
    if markers["monkey"] != 0:
        screen.blit(monkey_sprite,(window_dim[0]-(markers["monkey"]/60)*window_dim[0],0))
        markers["monkey"] -= 1
    if sock != '':
        read_ready, write_ready, error_ready=select.select([sock],[sock],[],0)

    for e in event.get():
        if e.type == QUIT:
            running=False
        elif e.type == MOUSEBUTTONUP and state not in game_overs and not markers["freeze"]:
            pos=mouse.get_pos()
            if state != "game":
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
                    if card != None :
                        if card.rect.collidepoint(pos):
                            selected=card
                        for item in card.items:
                            if card.items[item].rect.collidepoint(pos):
                                selected=card.items[item]
                for card in player1.hand:
                    if card.rect.collidepoint(pos):
                        selected=card
                for card in player2.field:
                    if card != None:
                        if card.rect.collidepoint(pos):
                            selected=card
                        for item in card.items:
                            if card.items[item].rect.collidepoint(pos):
                                selected=card.items[item]
                for card in player2.hand:
                    if card.rect.collidepoint(pos) and card.current_sprite != card.back_sprite:
                        selected=card
                if move_hovering_over != None:
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
                            player1.add_to_field(player1.hand.index(selected),i+1)
                            if setup == True:
                                abs_subturn += 1
                                abs_abs_subturn += 1
                        else:
                            if markers["not enough souls"][0] == 0 and min(hand_cost) >= player1.souls:
                                markers["not enough souls"]=[6,5,0,0] #[amount of cycles,frames per cycle,current colour,frame number]

            if attack_progressing:
                if type(selected) == Mob and markers["item stealing"][0] == False:
                    for card in targets:
                        if card != None and card.rect.collidepoint(pos) and setup == False:
                            result=None
                            target=card
                            if type(selected_move) != Ability:
                                counter=selected_move(origin=selected,target=target,player=player1,noattack=False)
                                if len(target.moveset) > 0:
                                    other_counter=target.moveset[0](origin=target,target=selected,player=player2,noattack=True)
                                else:
                                    counter=False
                                    other_counter=not counter
                                #selected.startmove([(target.rect.x,target.rect.y),(selected.rect.x,selected.rect.y)],[10,10])
                                if (counter == True or counter == other_counter) and len(target.moveset) > 0:
                                    card.moveset[0](origin=target,target=selected,player=player2,noattack=False)
                            else:
                                result=selected_move.effect(origin=selected,target=target,player=player1)
                            if until_end == 0:
                                if selected != None:
                                    if "end this turn" in selected.passives:
                                        selected.passives['end this turn'](origin=selected,player=player1)
                                    if selected.status["psn"] > 0:
                                        selected.health -= 1
                                        selected.status["psn"] -= 1
                                if player2.field[subturn-1] != None:
                                    if "end this turn" in player2.field[subturn-1].passives:
                                        player2.field[subturn-1].passives["end this turn"](origin=player2.field[subturn-1],player=player2)
                                    if player2.field[subturn-1].status["psn"] > 0:
                                        player2.field[subturn-1].health -= 1
                                        player2.field[subturn-1].status["psn"] -= 1
                                if postsubturn == 1 and setup == False:
                                    abs_subturn += 1
                                    abs_abs_subturn += 1
                                    markers["start of move called"]=False
                                if abs_abs_subturn != 3:
                                    selected = player1.field[abs_subturn%len(filled_positions)]
                                else:
                                    selected=player1.field[0]
                                    postsubturn += 1
                                attack_progressing=False
                                selected_move=None
                                move_hovering_over=None
                                targets=[]
                                if result == "break":
                                    break
                            else:
                                until_end -= 1
                                markers["until end just changed"]=True
                if type(selected) == Item and markers["item stealing"][0] == False:
                    for card in targets:
                        if card != None and card.rect.collidepoint(pos) and setup == False:
                            if not selected.cost > player1.souls:
                                if card in player1.field:
                                    player1.add_to_field(player1.hand.index(selected),player1.field.index(card)+1)
                                elif card in player2.field:
                                    player2.add_to_field(None,player2.field.index(card)+1,ignore_cost=True,card_override=selected,pos_override=card)
                                    player1.hand.pop(player1.hand.index(selected))
                                    player1.souls -= selected.cost
                                if targets == [whole_field]:
                                    player1.add_to_field(0,0,False,card_override=selected,pos_override=card)
                                if until_end == 0:
                                    if player1.field[subturn-1] != None:
                                        if "end this turn" in player1.field[subturn-1].passives:
                                            player1.field[subturn-1].passives["end this turn"](origin=player1.field[subturn-1],player=player1)
                                        if player1.field[subturn-1].status["psn"] > 0:
                                            player1.field[subturn-1].health -= 1
                                            player1.field[subturn-1].status["psn"] -= 1
                                    if player2.field[subturn-1] != None:
                                        if "end this turn" in player2.field[subturn-1].passives:
                                            player2.field[subturn-1].passives["end this turn"](origin=player2.field[subturn-1],player=player2)
                                        if player2.field[subturn-1].status["psn"] > 0:
                                            player2.field[subturn-1].health -= 1
                                            player2.field[subturn-1].status["psn"] -= 1
                                    if postsubturn == 1 and setup == False:
                                        abs_subturn += 1
                                        abs_abs_subturn += 1
                                        markers["start of move called"]=False
                                    if abs_abs_subturn != 3:
                                        selected = player1.field[abs_subturn%len(filled_positions)]
                                    else:
                                        selected=player1.field[0]
                                        postsubturn += 1
                                    attack_progressing=False
                                    selected_move=None
                                    move_hovering_over=None
                                    targets=[]
                                else:
                                    targets=selected.find_targets()
                                    until_end -= 1
                                    markers["until end just changed"]=True
                            else:
                                if markers["not enough souls"][0] == 0:
                                    markers["not enough souls"]=[6,5,0,0]
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
                markers["just chose"]=False

        elif e.type == MOUSEBUTTONUP and state in game_overs:
            pos = mouse.get_pos()
            if to_menu_text.textrect.collidepoint(pos):
                state = "menu"
                connect_state="idle"
                deck=[]
                turn=0
                setup=True
                subturn=1
                abs_subturn=1
                abs_abs_subturn=1
                postsubturn=1
                attack_choosing_state=False
                HOST=''
                sock=''
                markers={"retry":False, "deck built":False, "do not connect":True, "start of turn called":False, "not enough souls":[0,0,0,0], "data received, proceed":False, "just chose":False, "finishable":True, "freeze":False, "game over called":False, "fade":[0,[0,0,0],0,0,0], "start of move called":False,"item stealing":(False, None),"forage":False,"monkey":0,"until end just changed":False}
                selected=None
                selected_move=None
                attack_progressing=False
                move_hovering_over=None
                player2=''
                player1.reset()
        
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

    elif state == "game" or state in game_overs:
        if markers["deck built"] == False:
            turn = 1
            deck = deckbuilder(decklist)
            mob_deck=[card for card in deck if type(card)==Mob]
            for i in range(3):
                player2.hand.append(mob_deck.pop())
                player2.add_to_field(0,i+1,True)
            deck = [card for card in deck if card not in player2.field]
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
        if turn == 1:
            player1.souls = 10
        if not markers["do not connect"]:
            screen.blit(game_plc_text,(window_dim[0]/2-mjgs.size("Await further programming")[0]/2,window_dim[1]/2))
        screen.blit(deck_plc.current_sprite,(deck_plc.rect.x,deck_plc.rect.y))
        screen.blit(whole_field.current_sprite,(fields_anchor[0],fields_anchor[1]))
        if setup == True or abs_subturn > 2:
            screen.blit(subturn_sprites[0],(760,210))
        else:
            screen.blit(subturn_sprites[abs_subturn+1],(760,210))
        if selected != None:
            large_image=transform.scale(image.load(selected.original_sprite),(card_dim[0]*3,card_dim[1]*3)).convert()
            draw.rect(screen,ORANGE,Rect(selected.rect.x-5,selected.rect.y-5,selected.rect.width+10,selected.rect.height+10),5)
            screen.blit(large_image,(930,100))
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
                    player1.field[postsubturn-2].passives["end of turn"](origin=player1.field[postsubturn-2],player=player1)
                    skippost=False
                if "end of turn" in player1.field[postsubturn-2].items:
                    player1.field[postsubturn-2].items["end of turn"].effect(origin=player1.field[postsubturn-2],player=player1)
                    skippost=False
            if skippost:
                postsubturn += 1
        hand_cost=[]
        for card in player1.hand:
            if type(card) == Mob:
                hand_cost.append(card.cost)
            else:
                hand_cost.append(99)
        if min(hand_cost) >= player1.souls and setup == True:
            abs_subturn += 1
            abs_abs_subturn += 1
        if postsubturn >= 5 and setup == False:
            subturn = 1
            abs_subturn = 0
            abs_abs_subturn = 0
            postsubturn = 1
            turn += 1
            markers["start of turn called"] = False
            for card in player1.field:
                if card != None and card.status["aquatised"] > 0:
                    card.status["aquatised"] -= 1
            for card in player2.field:
                if card != None and card.status["aquatised"] > 0:
                    card.status["aquatised"] -= 1
        if abs_abs_subturn >= 4 and setup == True:
            setup=False
            subturn=1
            abs_subturn=0
            abs_abs_subturn=0
            player1.souls=1
            player2.souls=1
        filled_positions={}
        for i in range(len(player1.field)):
            if player1.field[i] != None:
                filled_positions[i] = player1.field[i]
        if len(filled_positions) > 0:
            subturn=list(filled_positions.keys())[abs_subturn%len(filled_positions)]+1
        if postsubturn == 1:
            draw.rect(screen,(255,255,255),Rect(player1.field_pos[subturn-1][0],player1.field_pos[subturn-1][1]+cut_dim[1]+10,cut_dim[0],10))
            if markers["start of move called"] == False and player1.field[subturn-1] != None and "on this turn" in player1.field[subturn-1].passives:
                player1.field[subturn-1].passives["on this turn"](player=player1,origin=player1.field[subturn-1])
                markers["start of move called"]=True
        else:
            draw.rect(screen,(255,255,255),Rect(player1.field_pos[postsubturn-2][0],player1.field_pos[postsubturn-2][1]+cut_dim[1]+10,cut_dim[0],10))
        player1.update()
        player2.update()
        for card in targets:
            if card != None:
                temp=Rect(card.rect.x,card.rect.y,card.rect.width,card.rect.height)
                draw.rect(screen,ORANGE,temp,5)
                draw.rect(screen,(255,255,255),Rect(temp.centerx-20,temp.centery-5,40,10))
                draw.rect(screen,(255,255,255),Rect(temp.centerx-5,temp.centery-20,10,40))
        if markers["finishable"] and setup == False and not markers["game over called"]:
            if player1.field == [None, None, None]:
                state = "lose"
                markers["freeze"]=True
                markers["fade"]=[60,[0,0,0],255,0,0] #duration in frames, final colour, final transparency, current transparency, transparency change per frame
                markers["game over called"]=True
                markers["fade"][4]=markers["fade"][2]/markers["fade"][0]
            if player2.field == [None, None, None]:
                state = "win"
                markers["freeze"]=True
                markers["fade"]=[60,[10,140,50],255,0,0]
                markers["fade"][4]=markers["fade"][2]/markers["fade"][0]
                markers["game over called"]=True
            if player1.field == [None, None, None] and player2.field == [None, None, None]:
                state ="tie"
                markers["freeze"]=True
                markers["fade"]=[60,[10,220,70],255,0,0]
                markers["fade"][4]=markers["fade"][2]/markers["fade"][0]
                markers["game over called"]=True
        screen.blit(mjgs.render(f"Abs:{str(abs_subturn)}, Sub:{str(subturn)}",True,(255,255,255)),(0,0))

    colourval = markers["fade"][1]+[markers["fade"][3]]
    temps=Surface(window_dim)
    temps.set_alpha(markers["fade"][3])
    temps.fill(markers["fade"][1])
    screen.blit(temps,(0,0))
    if setup == False:
        if state == "lose":
            if markers["fade"][0] <= 0:
                screen.blit(lose_text,(window_dim[0]/2-large_font.size("You lost...")[0]/2,window_dim[1]/2-100))
                screen.blit(skill_issue_text,(window_dim[0]/2-small_font.size("skill issue")[0]/2,window_dim[1]/2))
                screen.blit(to_menu_text.text, to_menu_text.position)
            else:
                markers["fade"][0]-=1
                markers["fade"][3]+=markers["fade"][4]

        if state == "win":
            if markers["fade"][0] <= 0:
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
    3. Figure out animations: card going from hand to field, card attacking, start of turn animations
    4. Implement putting multiple items of the same type onto mobs
    5. Does item application count as a subturn?
    6. Make quick strike a call to an attack instead of a messy code block inside atk_check
    7. Move item use depletion into itm_check instead of being called wherever an item is
    8. Get item stealing to work
    9. Line 1238: don't constantly load images, only do it when selected changes

    Conditions:
    "end of turn": Called at the end of the attack phase
    "start of turn": Called at the start of the turn, in the function start_of_turn()
    "on death": Called when health is 0
    "on hurt": Called when health decreases
    "on attack": Called when this attacks
    "on this turn: Called at the start of this mob's move
    "end this turn": Called immediately after this mob's move
    "when played": Called immediately
    "always": checks all the time
    '''