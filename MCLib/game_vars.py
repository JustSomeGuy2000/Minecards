from pygame import *
from MCLib.const import *

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
        self.animations:list=[]
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