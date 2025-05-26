from pygame import *
from MCLib.game_vars import Game
from MCLib.minor_classes import *
from MCLib.const import *

v=Game()

mp=mouse.get_pos()
dt=0
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
    kp=key.get_pressed()
    km=key.get_mods()
    dwx=0
    dwy=0
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
            kp.append(e)
        elif e.type == WINDOWSIZECHANGED:
            dwx=e.x
            dwy=e.y
    event_suite:Events=Events(md,mu,dmx,dmy,kp,km,msx,msy,mp,dwx,dwy,dt)

    display.update()
    dt=v.clock.tick(v.FPS)
