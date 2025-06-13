from typing import *
from pygame import *
font.init()

type Coord=tuple[int,int]
type Colour=tuple[int,int,int]|tuple[int,int,int,int]
type Path=str
type Condition=str
type MoveType=str

BASE_WIN_X=1536
BASE_WIN_Y=860

MAIN_MENU="Main Menu"

MJGS_M=font.Font(r"Assets\mojangles.ttf",40)
MJGS_S=font.Font(r"Assets\mojangles.ttf",20)
MJGS_L=font.Font(r"Assets\mojangles.ttf",80)

BLACK:Colour=(0,0,0)
WHITE:Colour=(255,255,255)
ORANGE:Colour=(255,180,0)

ALIGN_CENTER="center"
ALIGN_LEFT="left"
ALIGN_RIGHT="right"
ALIGN_TOP="top"
ALIGN_BOTTOM="bottom"

AS_ABSOLUTE="Absolute coordinates"
AS_RATIO="Ratio according to base screen size"

AS_PATH="String is a path"
AS_STR="String is a string to be rendered by the font"

CARD_DIM:Coord=(150,225)
CUT_DIM:Coord=(170,170)

IS_ATTACK:MoveType="This move is an attack"
IS_PASSIVE:MoveType="This move is a passive"
IS_ABILITY:MoveType="This move is an ability"
IS_ITEM:MoveType="This move belongs to an item"

END_OF_CYCLE:Condition="When this cycle ends"
START_OF_CYCLE:Condition="When this cycle starts"
END_OF_TURN:Condition="After this moves"
START_OF_TURN:Condition="Before this moves"
ON_DEATH:Condition="When this dies"
ON_HURT:Condition="When this loses health"
ON_ATTACK:Condition="When this attacks"
ON_ABILITY:Condition="When this uses an ability"
ON_PASSIVE:Condition="When this uses a passive"
WHEN_PLAYED:Condition="Activates immediately"
ALWAYS:Condition="Checked every frame"

STARTING_SOULS=20