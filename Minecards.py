from pygame import *
from MCLib.const import *

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
        self.dt=dt #change in time since last frame

class Game():
    def __init__(self):
        init()
        self.scrinfo=display.Info()
        self.win_height:int=self.scrinfo.current_h-100
        self.win_width:int=self.scrinfo.current_w
        self.win_dim=(self.win_width,self.win_height)
        self.screen=display.set_mode(self.win_dim,RESIZABLE)
        display.set_caption("Minecards")
        self.running:bool=True
        self.background:Surface=transform.scale(image.load(r"Assets\background.png"),self.win_dim).convert()
        self.FPS=60
        self.clock=time.Clock()
        self.menu:str=MAIN_MENU
        self.animations:list[Animation]=[]
        self.hold:bool=False

    def update_anims(self,events):
        holds:list[bool]=[]
        for anim in self.animations:
            result=anim.update(events,self)
            holds.append(anim.hold)
            
        if any(holds):
            self.hold=True
        else:
            self.hold=False

v=Game()

class Proportion():
    def __init__(self,x_pos:int,y_pos:int,abs_x:int=BASE_WIN_X,abs_y:int=BASE_WIN_Y):
        self.x=int(x_pos)
        self.y=int(y_pos)
        self.abs_x=abs_x
        self.abs_y=abs_y
        self.ratio_x:float=x_pos/abs_x
        self.ratio_y:float=y_pos/abs_y

    def gen_pos(self,width:int,height:int) -> Coord:
        return (int(self.ratio_x*width),int(self.ratio_y*height))
    
class Element():
    def __init__(self, x_pos:int, y_pos:int, img:Surface|str, str_type=AS_STR, image_size:Coord|None=None,x_align_type:str=ALIGN_CENTER, y_align_type:str=ALIGN_CENTER, x_coord_type=AS_ABSOLUTE, y_coord_type=AS_ABSOLUTE, on_click:Callable[[Game],None]|None=None, font:font.Font=MJGS_M, colour:Colour=BLACK):
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

class Menu():
    def __init__(self,elements:list[Element],identifier):
        self.elements=elements
        self.identifier=identifier
 
    def display(self,surface:Surface,events:Events,game:Game):
        for element in self.elements:
            element.display(surface,events,game)

class Animation():
    def __init__(self,duration:float,target:Element,next=None,hold:bool=False,*args):
        self.duration=duration
        self.current:float=0.0
        self.target=target
        self.next:None|Animation|Callable[[Animation,Game],Animation]=next
        self.updater:Callable[[Animation,Game],Any]=None
        self.update_args=args
        self.hold:bool=hold
    
    @classmethod
    def set_updater(cls,updater:Callable[[Self,Game],Any]):
        cls.updater=updater

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
    
def make_animation(updater:Callable[[Animation,Game],Any], name:str) -> type:
    '''Make an animation using updater as the animation function. The variable it is bound to should be as the name passed as an argument. Not doing so may cause strange effects.'''
    new_anim:Animation=type(name,(Animation))
    new_anim.set_updater(updater)
    return new_anim


title=Element(0.5,165,r"Assets\title.png",x_coord_type=AS_RATIO,image_size=(842,120),str_type=AS_PATH)
beta_text=Element(0.5,270,"Closed Beta (Rebuild)",font=MJGS_M,colour=ORANGE,x_coord_type=AS_RATIO,str_type=AS_STR)
start_game_text=Element(0.5,450,"Singleplayer",x_coord_type=AS_RATIO,str_type=AS_STR)
host_game_text=Element(7/18,550,"Host Game",x_coord_type=AS_RATIO,font=MJGS_M,str_type=AS_STR)
join_game_text=Element(11/18,550,"Join Game",x_coord_type=AS_RATIO,font=MJGS_M,str_type=AS_STR)
to_decks_text=Element(0.5,650,"Decks",str_type=AS_STR,x_coord_type=AS_RATIO)

main_menu=Menu([title,beta_text,host_game_text,join_game_text,start_game_text,to_decks_text],MAIN_MENU)

mp=mouse.get_pos()
dt=0
debug:bool=True
while v.running:
    v.screen.blit(v.background,(0,0))

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

    if v.menu == MAIN_MENU:
        main_menu.display(v.screen,event_suite,v)

    if debug:
        mp_text=MJGS_S.render("  "+str(mp),True,BLACK)
        draw.rect(v.screen,WHITE,mp_text.get_rect(x=mp[0],y=mp[1]))
        v.screen.blit(mp_text,mp)
    display.update()
    dt=v.clock.tick(v.FPS)
