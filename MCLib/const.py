import itertools as its
import enum
from typing import *
from pygame import *
init()

type Coord=tuple[int,int]
type Colour=tuple[int,int,int]|tuple[int,int,int,int]
type Path=str

#window-related constants
BASE_WIN_X=1536
BASE_WIN_Y=860
SCRINFO=display.Info()
WIN_H:int=SCRINFO.current_h-100
WIN_W:int=SCRINFO.current_w
WIN_DIM=(WIN_W,WIN_H)
screen=display.set_mode(WIN_DIM,RESIZABLE)
display.set_caption("Minecards")

#menu identifiers
class MenuNames(enum.Enum):
    MAIN_MENU="Main Menu"
    GAME_MENU="Game Menu"

#base fonts
MJGS_M=font.Font(r"Assets\mojangles.ttf",40)
MJGS_S=font.Font(r"Assets\mojangles.ttf",20)
MJGS_L=font.Font(r"Assets\mojangles.ttf",80)

#basic colours
BLACK=(0,0,0)
WHITE=(255,255,255)
ORANGE=(255,180,0)

#Argument interpretation constants for Element
ALIGN_CENTER="center"
ALIGN_LEFT="left"
ALIGN_RIGHT="right"
ALIGN_TOP="top"
ALIGN_BOTTOM="bottom"

AS_ABSOLUTE="Absolute coordinates"
AS_RATIO="Ratio according to base screen size"

AS_PATH="String is a path"
AS_STR="String is a string to be rendered by the font"

#card-related constants
CARD_DIM=(150,225)
CUT_DIM=(170,170)
CARDBACK=image.load("Assets\\Backs\\default.png").convert_alpha()

#layout-related constants
P1_HAND=(90,680)
P2_HAND=(90,-100)
FIELD_X_SPACING=70
HAND_TO_FIELD_SPACING=50
P1_FIELD=[(P1_HAND[0]+CUT_DIM[0]*i+FIELD_X_SPACING*i,P1_HAND[1]-HAND_TO_FIELD_SPACING) for i in range(3)]
P2_FIELD=[(P2_HAND[0]+CUT_DIM[0]*i+FIELD_X_SPACING*i,P2_HAND[1]+HAND_TO_FIELD_SPACING+CARD_DIM[1]) for i in range(3)]

class MoveType(enum.Enum):
    IS_ATTACK="This move is an attack"
    IS_PASSIVE="This move is a passive"
    IS_ABILITY="This move is an ability"
    IS_ITEM="This move belongs to an item"

class Condition(enum.Enum):
    END_OF_CYCLE="When this cycle ends"
    START_OF_CYCLE="When this cycle starts"
    END_OF_TURN="After this moves"
    START_OF_TURN="Before this moves"
    ON_DEATH="When this dies"
    ON_HURT="When this loses health"
    ON_ATTACK="When this attacks"
    ON_ABILITY="When this uses an ability"
    ON_PASSIVE="When this uses a passive"
    WHEN_PLAYED="Activates immediately"
    ALWAYS="Checked every frame"

class LScope(enum.Enum):
    FIELD="Triggered by cards on the field"
    HAND="Triggered by cards in a hand"
    SELF="Triggered by this card"
    ANY="Triggered by cards anywhere"

class PScope(enum.Enum):
    OWN_SIDE="Triggered by cards on this card's own side"
    OPP_SIDE="Triggered by cards on the opponent's side"
    SELF="Triggered by this card"
    ANY="Triggered by any side's card"

class Scope():
    def __init__(self, player_scope:PScope, loc_scope:LScope):
        self.player_scope=player_scope
        self.loc_scope=loc_scope

#misc game constants
STARTING_SOULS=20