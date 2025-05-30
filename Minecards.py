from pygame import *
from MCLib.game_vars import Game
from MCLib.minor_classes import *
from MCLib.const import *
from MCLib.ui import *

v=Game()

title=Element(0.5,165,r"Assets\title.png",x_coord_type=AS_RATIO,image_size=(842,120),str_type=AS_PATH)
beta_text=Element(0.5,270,"Closed Beta (Rebuild)",font=MJGS_M,colour=ORANGE,x_coord_type=AS_RATIO,str_type=AS_STR)
start_game_text=Element(0.5,450,"Singleplayer",x_coord_type=AS_RATIO,str_type=AS_STR)
host_game_text=Element(7/18,550,"Host Game",x_coord_type=AS_RATIO,font=MJGS_M,str_type=AS_STR)
join_game_text=Element(11/18,550,"Join Game",x_coord_type=AS_RATIO,font=MJGS_M,str_type=AS_STR)
to_decks_text=Element(0.5,650,"Decks",str_type=AS_STR,x_coord_type=AS_RATIO)

main_menu=Menu([title,beta_text,host_game_text,join_game_text,start_game_text,to_decks_text],MAIN_MENU)

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
        elif e.type == VIDEORESIZE:
            v.background=transform.scale(v.background,e.size)
    event_suite:Events=Events(md,mu,dmx,dmy,kp_current,km,msx,msy,mp,wx,wy,dt,kp_frame)

    if v.menu == MAIN_MENU:
        main_menu.display(v.screen,event_suite,v)

    mp_text=MJGS_S.render("  "+str(mp),True,BLACK)
    draw.rect(v.screen,WHITE,mp_text.get_rect(x=mp[0],y=mp[1]))
    v.screen.blit(mp_text,mp)
    display.update()
    dt=v.clock.tick(v.FPS)
