from typing import Callable, Any
from pygame import *
font.init()

type Coord=tuple[int,int]
type Colour=tuple[int,int,int]|tuple[int,int,int,int]

BASE_WIN_X=1536
BASE_WIN_Y=860

MAIN_MENU="Main Menu"

MJGS_M=font.Font(r"Assets\mojangles.ttf",40)
MJGS_S=font.Font(r"Assets\mojangles.ttf",20)
MJGS_L=font.Font(r"Assets\mojangles.ttf",80)

BLACK:Colour=(0,0,0)
WHITE:Colour=(255,255,255)
ORANGE:Colour=(255,180,0)

ALIGN_CENTER="Align center"
ALIGN_CORNER="Align corner"

AS_ABSOLUTE="Absolute coordinates"
AS_RATIO="Ratio according to base screen size"

AS_PATH="String is a path"
AS_STR="String is a string to be rendered by the font"