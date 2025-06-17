from __future__ import annotations
from MCLib.const import *

class Displayable():
    """Classes that have the display() method."""
    def __init__(self):
        pass

    def display(self, surface:Surface, events:Events, game:Game):
        pass

class Events():
    def __init__(self,md:bool=False,mu:bool=False,dmx:int=0,dmy:int=0,kp_current:key.ScancodeWrapper={},km:int=0,msx:int=0,msy:int=0,mp:tuple[int,int]=(0,0),wx:int=0,wy:int=0,dt=0,kp_frame:list[event.Event]=[]):
        self.md=md #mouse down
        self.mu=mu #mouse up
        self.dmx=dmx #change in mouse x
        self.dmy=dmy #change in mouse y
        self.kp_current=kp_current #state of all keys
        self.kp_frame=kp_frame #keys pressed on the current frame
        self.km=km #key modifiers pressed
        self.msx=msx #x component of mouse scroll
        self.msy=msy #y component of mouse scroll
        self.mp=mp #mouse position
        self.wx=wx #window width
        self.wy=wy #window height
        self.wd=(wx, wy) #gathered window dimensions
        self.dt=dt #change in time since last frame

class Game():
    def __init__(self): 
        self.running:bool=True
        self.background:Surface=transform.scale(image.load(r"Assets\background.png"),WIN_DIM).convert_alpha()
        self.FPS=60
        self.clock=time.Clock()
        self.menu:str=MenuNames.MAIN_MENU
        self.animations:list[Animation]=[]
        self.hold:bool=False
        self.player1:Player|None=None
        self.player2:Player|None=None

    def update_anims(self,events:Events):
        holds:list[bool]=[]
        remove:list[Animation]=[]
        add:list[Animation]=[]
        for anim in self.animations:
            result=anim.update(events,self)
            holds.append(anim.hold)
            if isinstance(result, Animation):
                if anim.current >= anim.duration:
                    remove.append(anim)
                add.append(result)
            elif result == None:
                remove.append(anim)
        for anim in remove:
            self.animations.remove(anim)
        self.animations.extend(add)
        if any(holds):
            self.hold=True
        else:
            self.hold=False

    def publish(self, event:Condition):
        ...

v=Game()
    
class Element(Displayable):
    def __init__(self, x_pos:int|float, y_pos:int|float, img:Surface|str, str_type=AS_STR, image_size:Coord|None=None,x_align_type:str=ALIGN_CENTER, y_align_type:str=ALIGN_CENTER, x_coord_type=AS_ABSOLUTE, y_coord_type=AS_ABSOLUTE, on_click:Callable[[Game],None]|None=None, font:font.Font=MJGS_M, colour:Colour=BLACK):
        if isinstance(img,Surface):
            self.img=img.convert_alpha()
            self.image_type="image"
        elif str_type == AS_STR:
            self.text=img
            self.img=font.render(img,True,colour)
            self.image_type="text"
            self.font=font
        elif str_type == AS_PATH:
            self.img=image.load(img).convert_alpha()
        if image_size != None:
            self.img=transform.scale(self.img,image_size)
        if x_coord_type == AS_RATIO:
            x_pos *= BASE_WIN_X
        if y_coord_type == AS_RATIO:
            y_pos *= BASE_WIN_Y
        self.position=Proportion(x_pos,y_pos)
        self.x_align_type=x_align_type
        self.y_align_type=y_align_type
        if self.x_align_type == ALIGN_CENTER:
            self.x_align_type = "centerx"
        if self.y_align_type == ALIGN_CENTER:
            self.y_align_type = "centery"
        self.rect:Rect=None
        exec(f"self.rect=self.img.get_rect({self.x_align_type}={x_pos},{self.y_align_type}={y_pos})")
        self.display_image=self.img
        self.on_click=on_click
        self.size=Proportion(self.rect.width,self.rect.height)
        self.last_win_dim:Coord=(BASE_WIN_X,BASE_WIN_Y)

    def display(self,surface:Surface,events:Events,game:Game):
        '''Note: The code here for compensating for screen size changes is kinda wonky. Revisit when possible.'''
        win_dim:Coord=(events.wx,events.wy)
        if win_dim != self.last_win_dim:
            new_x, new_y=self.position.gen_pos(win_dim[0],win_dim[1])
            exec(f"self.rect=self.img.get_rect({self.x_align_type}={new_x},{self.y_align_type}={new_y})")
            self.rect.width,self.rect.height=self.size.gen_pos(win_dim[0],win_dim[1])
            #self.display_image=transform.scale(self.image,(self.rect.width,self.rect.height))
            self.last_win_dim=win_dim
        surface.blit(self.display_image,self.rect)
        if events.mu and self.rect.collidepoint(events.mp) and self.on_click != None:
            self.on_click(game)

    def reposition(self, new:Coord, win_dim:Coord):
        '''Change the position of this object on the screen.'''
        self.position=Proportion(new[0],new[1],win_dim[0],win_dim[1])
        self.rect.topleft=new

    def realign(self, win_dim:Coord):
        '''Bring this object's position in line with the screen dimensions.'''
        self.rect.topleft=self.position.gen_pos(win_dim[0],win_dim[1])

class Menu(Displayable):
    def __init__(self,elements:list[Displayable],identifier):
        self.elements=elements
        self.identifier=identifier
 
    def display(self,surface:Surface,events:Events,game:Game):
        for element in self.elements:
            element.display(surface,events,game)

class Animation():
    def __init__(self,duration:float,target:Element,next:None|Self|Callable[[Self,Game],Self]=None,hold:bool=False,**kwargs):
        self.duration=duration
        self.current:float=0.0
        self.target=target
        self.next=next
        self.updater:Callable[[Animation,Game],Any]=None
        self.update_kwargs=kwargs
        self.hold:bool=hold

    def update(self,events:Events,game:Game):
        self.current += events.dt
        if self.current >= self.duration:
            if isinstance(self.next,Callable):
                return self.next(self,game)
            elif isinstance(self.next,Animation):
                return self.next
            else:
                return None
        result=self.updater(self,game)
        return result

class Slot(Displayable):
    def __init__(self, owned_by:Player, pos:Coord, size:Coord=CUT_DIM):
        self.owner=owned_by
        self.pos=Proportion(pos[0],pos[1])
        self.rect=Rect(pos, size)

        self.contains:Card|None=None
        self.selected:bool=False
        self.targeted:bool=False
        self.is_my_turn:bool=False
        self.last_win_dim:Coord=(BASE_WIN_X, BASE_WIN_Y)

    def display(self, surface:Surface, events:Events, game:Game):
        if self.last_win_dim != (events.wx,events.wy):
            self.realign(events.wd)
            self.last_win_dim=events.wd
        if events.md:
            if self.rect.collidepoint(events.mp):
                self.selected=not self.selected
                if isinstance(self.owner.hand_selected, Mob):
                    self.owner.play_mob(self.owner.hand_selected, self)
            else:
                self.selected=False
        if isinstance(self.owner.hand_selected, Mob) and self.contains == None:
            self.targeted=True
        else:
            self.targeted=False
        if isinstance(self.contains, Card):
            self.contains.display(surface, events, game)
        if self.selected:
            draw.rect(surface,SELECT_COLOUR,self.rect,SELECT_WIDTH)
        if self.targeted:
            draw.rect(surface,SELECT_COLOUR,self.rect,SELECT_WIDTH)
            draw.rect(surface,WHITE,Rect(self.rect.left+0.25*self.rect.width,self.rect.top+0.45*self.rect.height,0.5*self.rect.width,0.1*self.rect.height)) #horizontal bar
            draw.rect(surface,WHITE,Rect(self.rect.left+0.45*self.rect.width,self.rect.top+0.25*self.rect.height,0.1*self.rect.width,0.5*self.rect.height)) #vertical bar
        if self.is_my_turn:
            draw.rect(surface,WHITE,Rect(self.rect.left,self.rect.bottom+TURN_BAR_SPACING,self.rect.width,TURN_BAR_HEIGHT))

    def reposition(self, new:Coord, win_dim:Coord):
        '''Change the position of this object on the screen.'''
        self.pos=Proportion(new[0],new[1],win_dim[0],win_dim[1])
        self.rect.topleft=new

    def realign(self, win_dim:Coord):
        '''Bring this object's position in line with the screen dimensions.'''
        self.rect.topleft=self.pos.gen_pos(win_dim[0],win_dim[1])

class Card(Displayable):
    def __init__(self, name:str, cost:int, border:BorderColour, id_num:int, front_sprite:Surface, cut_sprite:Surface, initpos:Coord=(0,0), large_size:Coord=CARD_DIM, cut_size:Coord=CUT_DIM, back_sprite:Surface=CARDBACK):
        self.name=name
        self.cost=cost
        self.border=border
        self.id_num=id_num
        self.initpos=initpos
        self.large_size=large_size
        self.cut_size=cut_size
        self.back_sprite=back_sprite
        self.front_sprite=transform.scale(front_sprite,large_size).convert_alpha()
        self.cut_sprite=transform.scale(cut_sprite,cut_size).convert_alpha()
        self.back_sprite=transform.scale(back_sprite,large_size).convert_alpha()
        self.large_image=transform.scale(front_sprite, LARGE_DIM).convert_alpha()
        self.current_sprite=self.back_sprite
        self.pos=Proportion(initpos[0],initpos[1])
        self.rect=self.current_sprite.get_rect(topleft=initpos)

        self.parent:Slot|None=None
        self.last_win_dim:Coord=(BASE_WIN_X,BASE_WIN_Y)
        self.playable:bool=True
        self.owned_by:Player|None=None
        self.visible:bool=False
        self.selected:bool=False
        self.targeted:bool=False

    def __deepcopy__(self, memo) -> Self:
        cls=self.__class__
        result=cls.__new__(cls)
        memo[id(self)]=result
        for k, v in self.__dict__.items():
            if isinstance(v, Surface):
                if DEEPCOPY_SURFACES:
                    setattr(result, k, v.copy())
                else:
                    setattr(result, k, copy.copy(v))
            elif isinstance(v, (Move, enum.Enum, enum.Flag)):
                setattr(result, k, copy.copy(v))
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result
    
    def display(self, surface:Surface, events:Events, game:Game) -> bool:
        '''Returns if the card was clicked or not.'''
        ret=False
        if self.last_win_dim != (events.wx,events.wy):
            self.realign(events.wd)
            self.last_win_dim=events.wd
        if events.md and self.current_sprite == self.front_sprite:
            if self.rect.collidepoint(events.mp):
                self.selected=not self.selected
                if self.selected:
                    ret=True
            else:
                self.selected=False
        if self.visible:
            surface.blit(self.current_sprite,self.rect)
        if self.selected:
            surface.blit(self.large_image, LARGE_IMAGE_POS.gen_pos(events.wx, events.wy))
        if not isinstance(self.parent, Slot):
            if self.selected:
                draw.rect(surface,SELECT_COLOUR,self.rect,SELECT_WIDTH)
            if self.targeted:
                draw.rect(surface,WHITE,Rect(self.rect.left+0.25*self.rect.width,self.rect.top+0.4*self.rect.height,0.5*self.rect.width,0.2*self.rect.height))
                draw.rect(surface,WHITE,Rect(self.rect.left+0.4*self.rect.width,self.rect.top+0.25*self.rect.height,0.2*self.rect.width,0.5*self.rect.height))
        return ret
    
    def reposition(self, new:Coord, win_dim:Coord=None):
        '''Change the position of this object on the screen.'''
        if win_dim == None:
            win_dim=screen.get_rect().size
        self.pos=Proportion(new[0],new[1],win_dim[0],win_dim[1])
        self.rect.topleft=new

    def realign(self, win_dim:Coord):
        '''Bring this object's position in line with the screen dimensions.'''
        self.rect.topleft=self.pos.gen_pos(win_dim[0],win_dim[1])

    def switch(self, switch_to:Literal["front","back","cut"]):
        '''Switch the sprite of the card.'''
        match switch_to:
            case "front":
                self.current_sprite=self.front_sprite
            case "back":
                self.current_sprite=self.back_sprite
            case "cut":
                self.current_sprite=self.cut_sprite
        self.rect=self.current_sprite.get_rect()

class Mob(Card):
    def __init__(self, name:str, cost:int, health:int, moves:list[Move], mob_class:MobClass, biome:Biome, border:BorderColour, front_sprite:Surface, cut_sprite:Surface, id_num:int, initpos:Coord=(0,0), large_size:Coord=CARD_DIM, cut_size:Coord=CUT_DIM, back_sprite:Surface=CARDBACK, **kwargs):
        super().__init__(name,cost,border,id_num,front_sprite,cut_sprite,initpos,large_size,cut_size,back_sprite)
        self.health=health
        self.moves=moves
        self.mob_class=mob_class
        self.biome=biome
        self.extras=kwargs

        self.items:list[Item]=[]
        self.proxy_for:Mob|None=None
        self.proxy:Mob|None=None

    def display(self, surface:Surface, events:Events, game:Game):
        super().display(surface, events, game)

    def attack(self, move_num:int, game:Game):
        '''Use an attack.'''
        ...

    def ability(self, event:Condition, game:Game):
        '''Use an ability'''
        ...

    def hurt(self, amount:int, game:Game):
        '''Reduce health. May kill the Mob.'''
        ...

    def heal(self, amount:int, game:Game, increase_cap:bool=False):
        '''Increase health. Will be capped at the mob's max health unless increase_cap is set to True'''
        ...

    def counter(self, target:Mob, game:Game):
        '''Counter-attack. Distinct from attack primarily in that it does not incite a counter of its own.'''
        ...

class Item(Card):
    def __init__(self, name:str, cost:int, effect:Move, border:str, front_sprite:Surface, cut_sprite:Surface, id_num:int, uses:int=1, initpos:Coord=(0,0), large_size:Coord=CARD_DIM, cut_size:Coord=ITEM_DIM, back_sprite:Surface=CARDBACK, **kwargs):
        super().__init__(name,cost,border,id_num,front_sprite,cut_sprite,initpos,large_size,cut_size,back_sprite)
        self.uses=uses
        self.effect=effect
        self.extras=kwargs

        self.attached_to:Mob|None=None

    def display(self, surface:Surface, events:Events, game:Game):
        super().display(surface, events, game)

    def use(self, target:Card, game:Game):
        ...

def build_deck(deckhint:dict[Cards,int], player:Player) -> list[Card]:
    '''Take in a dictionary with objects as keys and numbers as values, and output a list where each object appears as many times as its value. Deepcopy is used. Supposed to be used with decks, but since Python is dynamically typed, can be used for other things as well.'''
    result:list[Card]=[]
    for card in deckhint:
        for i in range(deckhint[card]):
            copied_card=copy.deepcopy(card.value)
            copied_card.owned_by=player
            result.append(copied_card)
    return result

class Player(Displayable):
    def __init__(self, id_num:int, hand_anchor:Coord, field_positions:list[Coord], name:str|None=None, deckhint:dict[Cards,int]={}):
        self.id_num=id_num
        self.hand_anchor=hand_anchor
        self.field_positions=field_positions
        self.name=name

        self.souls:int=STARTING_SOULS
        self.hand:list[Card]=[]
        self.field:list[Slot]=[Slot(self, field_positions[0]),Slot(self, field_positions[1]),Slot(self, field_positions[2])]
        self.deck:list[Card]=build_deck(deckhint, self)
        self.hand_selected:Card|None=None
        self.field_selected:Slot|None=None

    def display(self, surface:Surface, events:Events, game:Game):
        '''Display the hand and field.'''
        for card in self.hand:
           card.display(surface, events, game)
           if card.selected:
               self.hand_selected=card
        for slot in self.field:
            slot.display(surface, events, game)

    def next(self) -> Slot|None:
        '''Return the Slot whose turn is next. Returns None if no eligible slots are found.'''
        cycler=its.cycle(self.field)
        count:int=0
        while count < 4:
            target=next(cycler)
            if target.is_my_turn:
                break
            count += 1
        count=0
        while count < 4:
            target=next(cycler)
            if isinstance(target.contains, Mob):
                return target
            count+=1
        return None
    
    def add_to_hand(self, cards:Card|list[Card], win_dim:Coord):
        '''Add a card (or cards) to the end of the hand fron any source.'''
        if isinstance(cards, Card):
            cards=[cards]
        for card in cards:
            card.visible=True
            if self.id_num == 1:
                card.switch("front")
            card.reposition((self.hand_anchor[0]+CARD_DIM[0]*len(self.hand),self.hand_anchor[1]),win_dim)
            card.owned_by=self
            self.hand.append(card)

    def play_mob(self, card:Mob, slot:Slot):
        '''Play a mob onto the field.'''
        if not isinstance(card, Mob):
            warnings.warn("Attempted to play a non-mob card onto a field slot.")
            return
        if not card.playable:
            return
        if card in self.hand:
            self.hand.remove(card)
        card.switch("cut")
        card.reposition(slot.rect.topleft)
        slot.contains=card
        card.parent=slot
        self.reload_hand(screen.get_rect().size)

    def reload_hand(self, win_dim:Coord=None):
        '''Reload the positions of all the cards in the hand, in case position shenanigans are prone to occuring in a piece of code.'''
        if win_dim == None:
            win_dim=screen.get_rect().size
        for card in self.hand:
            card.reposition((self.hand_anchor[0]+CARD_DIM[0]*self.hand.index(card),self.hand_anchor[1]),win_dim)
    
    def draw(self, amount:int, win_dim:Coord) -> list[Card]:
        '''Draw cards from the deck and add them to the end of the hand.'''
        drew:list[Card]=[]
        for _ in range(amount):
            try:
                card=self.deck.pop()
            except:
                self.add_to_hand(drew, win_dim)
                return drew
            drew.append(card)
        self.add_to_hand(drew, win_dim)
        return drew
    
    def start_game(self) -> list[Card]:
        '''Set up the player for the start of the game.'''
        info=display.Info()
        wx, wy= info.current_w, info.current_h
        r.shuffle(self.hand)
        self.draw(STARTING_CARDS, (wx, wy))
        return self.hand

class MoveInfo():
    '''A data object (does not use dataclass since its attributes are meant to be mutable) holding information about the currently selected move.'''
    def __init__(self, type:MoveType, origin:Card|None, target:Card|None, player:Player|None, damage:int=0, block:bool=False, **kwargs):
        self.type=type
        self.origin=origin
        self.target=target
        self.player=player
        self.damage=damage
        self.block=block
        self.extras=kwargs

class Move():
    def __init__(self, name:str, type:MoveType, condition:list[Condition], effect:Callable[[MoveInfo,Game],None], targets:Callable[[MoveInfo,Game],None], scope:Scope, cost:int=0):
        self.name=name
        self.type=type
        self.condition=condition
        self.effect=effect
        self.targets=targets
        self.scope=scope
        self.cost=cost

    def use(self, info:MoveInfo, game:Game):
        return self.effect(info, game)

def gen_change_menu(menu:str):
    def change_menu(game:Game, menu:str=menu):
        game.menu=menu
    return change_menu

def start_game(game:Game):
    game.menu=MenuNames.GAME_MENU
    game.player1.start_game()
    game.player2.start_game()

class Cards(enum.Enum):
    Zombie=Mob("Zombie",2,4,[],MobClass.UNDEAD,Biome.CAVERN,BorderColour.BLUE,image.load("Sprites\\Zombie.png"),image.load("Cut Sprites\\Zombie.png"),0)

title=Element(0.5,165,r"Assets\title.png",x_coord_type=AS_RATIO,image_size=(842,120),str_type=AS_PATH)
beta_text=Element(0.5,270,"Closed Beta (Rebuild)",font=MJGS_M,colour=ORANGE,x_coord_type=AS_RATIO,str_type=AS_STR)
start_game_text=Element(0.5,450,"Singleplayer",x_coord_type=AS_RATIO,str_type=AS_STR,on_click=start_game)
host_game_text=Element(7/18,550,"Host Game",x_coord_type=AS_RATIO,font=MJGS_M,str_type=AS_STR)
join_game_text=Element(11/18,550,"Join Game",x_coord_type=AS_RATIO,font=MJGS_M,str_type=AS_STR)
to_decks_text=Element(0.5,650,"Decks",str_type=AS_STR,x_coord_type=AS_RATIO)

v.player1=Player(1,P1_HAND,P1_FIELD,"Player 1",deckhint={Cards.Zombie:40})
v.player2=Player(2,P2_HAND,P2_FIELD,"Player 2",deckhint={Cards.Zombie:40})

main_menu=Menu([title,beta_text,host_game_text,join_game_text,start_game_text,to_decks_text],MenuNames.MAIN_MENU)
game_menu=Menu([v.player1,v.player2],MenuNames.GAME_MENU)

mp=mouse.get_pos()
dt=0
debug:bool=True
while v.running:
    screen.blit(v.background,(0,0))

    md=False
    mu=False
    temp_mp=mouse.get_pos()
    dmx=temp_mp[0]-mp[0]
    dmy=temp_mp[1]-mp[1]
    msx=0
    msy=0
    mp=temp_mp
    kp_current=key.get_pressed()
    kp_frame:list[event.Event]=[]
    km=key.get_mods()
    scrinfo=display.Info()
    wx=scrinfo.current_w
    wy=scrinfo.current_h
    for e in event.get():
        if e.type == QUIT:
            v.running=False
        if v.hold:
            break
        elif e.type == MOUSEBUTTONDOWN:
            md=True
        elif e.type == MOUSEBUTTONUP:
            mu=True
        elif e.type == MOUSEWHEEL:
            msx=e.x
            msy=e.y
        elif e.type == KEYDOWN:
            kp_frame.append(e)
            if e.key == K_d:
                debug=not debug
        elif e.type == VIDEORESIZE:
            v.background=transform.scale(v.background,e.size)
    event_suite:Events=Events(md,mu,dmx,dmy,kp_current,km,msx,msy,mp,wx,wy,dt,kp_frame)

    if v.menu == MenuNames.MAIN_MENU:
        main_menu.display(screen,event_suite,v)
    elif v.menu == MenuNames.GAME_MENU:
        game_menu.display(screen,event_suite,v)
    v.update_anims(event_suite)

    if debug:
        mp_text=MJGS_S.render("  "+str(mp),True,BLACK)
        draw.rect(screen,WHITE,mp_text.get_rect(x=mp[0],y=mp[1]))
        screen.blit(mp_text,mp)

    display.update()
    dt=v.clock.tick(v.FPS)
