from __future__ import annotations
import typing
from MCLib.const import *
if typing.TYPE_CHECKING:
    from Minecards import *

class Move():
    def __init__(self, name:str, type:MoveType, effect:Callable[[MoveInfo,Game],None], targets:Callable[[MoveInfo,Game],None], scope:Scope=None, cost:int=0, ranged:bool=False, conditions:list[Condition]=[]):
        self.name=name
        self.type=type
        self.conditions=conditions
        self.effect=effect
        self.targets=targets
        self.scope=scope
        self.cost=cost
        self.ranged=ranged

    def use(self, info:MoveInfo, game:Game):
        return self.effect(info, game)
    
def gen_melee(dmg:int):
    def punch(info:MoveInfo, game:Game, dmg:int=dmg):
        ...
    return punch

def basic_opponents(info:MoveInfo, game:Game):
    return game.player2.field

bite=Move("Bite", MoveType.IS_ATTACK, gen_melee(2), basic_opponents)