import itertools as its
import random as r
import warnings
import copy
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

#menu identifiers
class MenuNames(enum.Enum):
    MAIN_MENU="Main Menu"
    GAME_MENU="Game Menu"

#base fonts
MJGS_M=font.Font(r"Assets\mojangles.ttf",40)
MJGS_S=font.Font(r"Assets\mojangles.ttf",20)
MJGS_L=font.Font(r"Assets\mojangles.ttf",80)
TW_CEN=font.Font("Assets\\tw-cen-mt-condensed-extrabold.ttf")

#basic colours
BLACK=(0,0,0)
WHITE=(255,255,255)
ORANGE=(255,180,0)
SELECT_COLOUR=ORANGE

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
ITEM_DIM=(75,75)
CARDBACK=image.load("Assets\\Backs\\default.png").convert_alpha()
SELECT_WIDTH=5
TURN_BAR_SPACING=20
TURN_BAR_HEIGHT=15
LARGE_DIM=(CARD_DIM[0]*3, CARD_DIM[1]*3)

#layout-related constants
P1_HAND=(90,680)
P2_HAND=(90,-100)
FIELD_X_SPACING=70
HAND_TO_FIELD_SPACING=50
P1_FIELD=[(P1_HAND[0]+CUT_DIM[0]*i+FIELD_X_SPACING*i,P1_HAND[1]-HAND_TO_FIELD_SPACING-CUT_DIM[1]) for i in range(3)]
P2_FIELD=[(P2_HAND[0]+CUT_DIM[0]*i+FIELD_X_SPACING*i,P2_HAND[1]+HAND_TO_FIELD_SPACING+CARD_DIM[1]-CUT_DIM[1]) for i in range(3)]
LARGE_IMAGE_POS=Proportion(930,10)

class MoveType(enum.Enum):
    IS_ATTACK="This move is an attack"
    IS_PASSIVE="This move is a passive"
    IS_ABILITY="This move is an ability"
    IS_ITEM="This move belongs to an item"

class Condition(enum.Flag):
    END_OF_CYCLE=enum.auto()
    START_OF_CYCLE=enum.auto()
    END_OF_TURN=enum.auto()
    START_OF_TURN=enum.auto()
    ON_DEATH=enum.auto()
    ON_HURT=enum.auto()
    ON_ATTACK=enum.auto()
    ON_ABILITY=enum.auto()
    ON_PASSIVE=enum.auto()
    WHEN_PLAYED=enum.auto()
    ALWAYS=enum.auto()

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

class MobClass(enum.Enum):
    UNDEAD="Undead"
    ARTHROPOD="Arthropod"
    AQUATIC="Aquatic"
    HUMAN="Human"
    MISC="Misc"

class Biome(enum.Enum):
    PLAINS="Plains"
    CAVERN="Cavern"
    OCEAN="Ocean"
    SWAMP="Swamp"

class BorderColour(enum.Enum):
    BLUE="Blue"
    PINK="Pink"

#misc game constants
STARTING_SOULS=20
STARTING_CARDS=5
DEEPCOPY_SURFACES=False