from __future__ import annotations
from pygame import *
from MCLib.const import *
from MCLib.minor_classes import Events
from MCLib.game_vars import Game

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
    def set_updater(cls,updater:Callable[[Animation,Game],Any]):
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
