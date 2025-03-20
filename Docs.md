# Conditions
"end of turn": Called at the end of the attack phase
"start of turn": Called at the start of the turn, in the function start_of_turn()
"on death": Called when health is 0
"on hurt": Called when health decreases
"on attack": Called when this attacks
"on this turn: Called at the start of this mob's move
"end this turn": Called immediately after this mob's move
"when played": Called immediately
"always": checks all the time

# Effect format and return requirements
## Attacks:
Attacks take 4 arguments: origin, target, player and noattack.
Origin is the attacking mob.
Target is the target mob.
Player is the player the attacking mob belongs to (since it's too late now to make player a variable of Card)
Noattack is a boolean value that dictates whether an attack actually takes place.

Attacks return two{three} values: [0]:bool, [1]:int, {[2]:list}.
[0] is a boolean value that is True for melee attacks and False for ranged ones.
[1] is the damage the attack deals.
[2] is a list of targets. The attack is executed on all of them. Can be omitted if there is only one target.

If noattack is True, damage is always 0 and any other effects don't take place.
This is to check whether moves should be countered or not.

Examples:
```py
@atk_check #single-target
def bite(**kwargs:Attack_params) -> tuple[Literal[True],Literal[2]]:
    dmg=0
    if kwargs["noattack"] == False:
        dmg=2
    return True, dmg

@atk_check #multi-target, hits everything except itself
def purple(**kwargs:Attack_params) -> tuple[Literal[False],int,list[Card]]:
    dmg=0
    if kwargs["noattack"] == False:
        dmg=3
    return False, dmg, [card for card in player1.field+player2.field if card != None]
```

## Passives:
Passives take four or five arguments: origin, target, player, loc and {damage}.
Origin is the mob that is attacking.
Target is the target mob.
Player is the player the attacking mob belongs to
Loc is the coordinates of the card that used the passive
    Used by psv_check to add to linger_anims
{Damage} is how much damage the target is receiving.
    Used only for "on hurt" passives.

Passives return one or two values: [0]:bool and {[1]:bool}.
[0] is a boolean value indicating if the passive's effect took place.
    This is used in psv_check() to set Mob.move_anim
[1] is only used in on death passives.
    If False, the mob does not die. Any other value and it does.

## Abilities
Abilities are differentiated from passives since they have to be chosen, and from attacks because they cannot be countered and usually deal no damage.
Abilities take four arguments: origin, target, player and loc.
Origin is the attacking mob.
Target is the target mob.
Player is the player the attacking mob belongs to.
Loc is the coordinates of the card that used the passive
    Used by psv_check to add to linger_anims

Abilities return one or two values: [0]:bool and {[1]:str}.
[0] is a boolean value indicating if the passive's effect took place.
    This is used in psv_check() to set Mob.move_anim
[1] is a versatile string used to modulate several routines.
    [1]="break", used by wool_guard(), stops the attack routine from cycling through the rest of the targets in the target list. I can't remember why this is needed but it's best not to touch it.

## Items
Item effects take six arguments: origin, target, player, item, only_targeting and original/damage.
Origin is the mob that is attacking.
Target is the target mob.
Player is the player the attacking mob belongs to.
Item is the item calling the effect.
Only_targeting is a boolean value specifying if only the target list should be returned.
    This should not be called externally. It is handled by itm_check()
Original/damage is the damage being dealt.
    Damage is used in "on hurt" items, while original is used in "on attack" items. Don't ask me why. Its probably going to cause trouble in the future.

Items return no values or one value: {[0]:list} and {[1]:list[bool,int,list]}.
[0] is a list of the item's targets.
    The effect is executed on all of them. Only returned if only_targeting is True. Can be [None].
[1] is the modified original value, composed of whether the attack is melee or ranged, its damage and its targets.
    Used only by "on attack" items.
    itm_check() uses this as the new attack value for the current card.

# Certain variables
## linger_anims
A list of tuples. Each tuple cotains:
[0]\:Surface: The surface to blit
[1]\:Coord: The starting position
[2]\:int: The current frame of the animation
[3]\:int: The max frame of the animation
[4]\:str: The equation used to show the animation.
    For now, takes values of "inverse up" or "inverse down", -/+ 1/x
[5]\:int: The scale of the animation.