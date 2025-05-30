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