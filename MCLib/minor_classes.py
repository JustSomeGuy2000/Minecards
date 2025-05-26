from pygame import *
from MCLib.const import *

class Events():
    def __init__(self,md:bool=False,mu:bool=False,dmx:int=0,dmy:int=0,kp:key.ScancodeWrapper={},km:int=0,msx:int=0,msy:int=0,mp:tuple[int,int]=(0,0),dwx:int=0,dwy:int=0,dt=0):
        self.md=md #mouse down
        self.mu=mu #mouse up
        self.dmx=dmx #change in mouse x
        self.dmy=dmy #change in mouse y
        self.kp=kp #state of all keys
        self.km=km #key modifiers pressed
        self.msx=msx #x component of mouse scroll
        self.msy=msy #y component of mouse scroll
        self.mp=mp #mouse position
        self.dwx=dwx #change in window width
        self.dwy=dwy #change in window height
        self.dt=dt #change in time since last frame