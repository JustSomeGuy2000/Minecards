from pygame import *
from MCLib.const import *
from MCLib.minor_classes import Events
from MCLib.game_vars import Game

class Position():
    def __init__(self,x_pos:int,y_pos:int):
        self.x=x_pos
        self.y=y_pos
        self.ratio_x:float=x_pos/1536
        self.ratio_y:float=y_pos/860

    def gen_pos(self,width:int,height:int) -> Coord:
        return (int(self.ratio_x*width),int(self.ratio_y*height))
    
class Element():
    def __init__(self,x_pos:int,y_pos:int,image:Surface|str,on_click:Callable[[Game],None],font:font.Font|None=None,colour:Colour|None=None):
        if isinstance(image,Surface):
            self.image=image
            self.image_type="image"
        else:
            self.text=image
            self.image=font.render(image,True,colour)
            self.image_type="text"
            self.font=font
        self.position=Position(x_pos,y_pos)
        self.rect=self.image.get_rect(top=y_pos,left=x_pos)
        self.on_click=on_click

    def display(self,surface:Surface,events:Events,game:Game):
        surface.blit(self.image,self.rect)
        if events.mu and self.rect.collidepoint(events.mp):
            self.on_click(game)

    def recolour(self,new:Colour):
        if self.image_type == "text":
            self.image=self.font.render(self.text,True,new)
