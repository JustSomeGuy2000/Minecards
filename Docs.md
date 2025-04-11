# Conditions
"end of turn": Called at the end of the attack phase
"start of turn": Called at the start of the turn, in the function start_of_turn()
"on death": Called when health is 0
    These can return a single value. If False, the mob does not die.
"on hurt": Called when health decreases
    These take an extra parameter "damage", how much damage the Mob took.
"on attack": Called when this attacks
    These take an extra parameter "original", the original attack tuple
    These return a modified attak tuple.
"on this turn: Called at the start of this mob's move
"end this turn": Called immediately after this mob's move
"when played": Called immediately
"always": Checks all the time
"on action": Called when an ability, or attack activates

# Actionable format and return requirements
## Attacks:
Attacks take 4 arguments: origin, target, player and noattack.
Origin is the attacking mob.
Target is the target mob.
Player is the player the attacking mob belongs to (since it's too late now to make player a variable of Card)
Noattack is a boolean value that dictates whether an attack actually takes place.

Attacks return two{three} basic values: [0]:bool, [1]:int, {[2]:list}.
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
Passives take four basic arguments: origin, target, player, loc.
Origin is the mob that is attacking.
Target is the target mob.
Player is the player the attacking mob belongs to
Loc is the coordinates of the card that used the passive
    Used by psv_check to add to linger_anims

Passives usually return one or two values: [0]:bool and {[1]:bool}.
[0] is a boolean value indicating if the passive's effect took place.
    This is used in psv_check() to set Mob.move_anim

## Abilities
Abilities are differentiated from passives since they have to be chosen, and from attacks because they cannot be countered and usually deal no damage.
Abilities take four basic arguments: origin, target, player and loc.
Origin is the attacking mob.
Target is the target mob.
Player is the player the attacking mob belongs to.
Loc is the coordinates of the card that used the ability
    Used by psv_check to add to linger_anims

Abilities usually return one or two values: [0]:bool and {[1]:str}.
[0] is a boolean value indicating if the ability's effect took place.
    This is used in psv_check() to set Mob.move_anim
[1] is a versatile string used to modulate several routines.
    [1]="break", used by wool_guard(), stops the attack routine from cycling through the rest of the targets in the target list. I can't remember why this is needed but it's best not to touch it.

## Items
Item effects take five basic arguments: origin, target, player, item and only_targeting.
Origin is the mob that is attacking.
Target is the target mob.
Player is the player the attacking mob belongs to.
Item is the item calling the effect.
Only_targeting is a boolean value specifying if only the target list should be returned.
    This should not be called externally. It is handled by itm_check()

Items usually return no to one value/s: {[0]:list}.
[0] is a list of the item's targets.
    The effect is executed on all of them. Only returned if only_targeting is True. Can be [None] if the item is not executed on a card (e.g. Loot Chest)

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

# Instruction string format
The instruction string is usually made of up to 5 characters: [0][1][2][3][4].
[0] is the type of instruction.
    "n" indicates sending the player's name.
    "c" indicates the player has conceded or exited.
    "m/i/a/p" indicates the player has used a card.
    "g" indicates the opponent is still connected
    "d" indicates a card has been drawn.
    "x" indicates the player has no moves and to proceed
    "t" indicates a timeout
If [0]="n", the following information is the name.
If [0]="c", there is no following information.
If [0]="m", the player used a mob move.
    [1] is the field position of the mob.
    [2] is the move number.
    [3] is the number of the target on the opponent's field
If [0]="i", the player used an item move.
    [1] is the hand position of the item.
    [2] is the field mob to play it onto. (3 is whole field targeting)
    [3] is the player whose field [2] refers to (not present if whole field targeting).
If [0]="a", the player used an ability.
    [1] is the field position of the mob.
    [2] is the ability number of the ability
    [3] is the target of the ability. (3 if whole field targeting)
    [4] is the player whose field [3] refers to (not present if whole field targeting).
If [0]="p", the player placed a mob down.
    [1] is the hand position of the mob.
    [2] is the field position to place to.
If [0]="g", there is no following information.
    In the abscence of commands, "g" is constantly written to the socket.
    If nothing is received, a countdown is started.
    If at the end of the countdown, still nothing is received, it is assumed the opponent has disconencted and the game ends with them conceding.
If [0]="d", the following one to two characters are the id number of the card that was drawn.
If [0]="x", there is no following information.
Note that the only information communicated is the player's direct action.
Any passives, items, etc. that activate are handled by the client.

# Player 2 move logic
Player 2's hand, field and souls are loaded into the function.
A random card is chosen from available_cards (a combination of the hand and the field) and is checked for playability. If it is not playable, the card is removed from available_cards and the cycle restarts. Otherwise, the instruction string is compiled, the loop is broken, and the function returns.

If the card is a mob, it is first checked whether it is in the hand or the field. If it is in the hand, a field slot is available, and the cardcan be afforded, the card is placed. Otherwise, the check fails.
If it is in the field, a random move or ability is chosen from its moveset. If a move is chosen, it is executed. If an ability is chosen and can be afforded, it is used. Otherwise, the check fails.

If the card is an item, if it can be afforded, it is placed onto a random targetable mob. If it is too expensive, the check fails.

# The turn system
Hoo boy. Thing is, I need to rewrite the turn system to support multiplayer, but when I tried, all sorts of stuff started happening. So, I'm going to write down how it all works, and hopefully that will give me a greater understanding of this convoluted mess.

the system is made of 4 variables:
[turn]\: the amount of turns that have passed since the start of the game.
[subturn]\: which card whould be attacking.
[abs_subturn]\: keeps track of how many subturns have passed.
[postsubturn]\: which card is currently being considered for "end of turn" actions.
[setup]\: whether the game is in the setup phase (when cards are first being placed).
[until_end]\: the number of turns until the turn is over. Usually 0.
```py
subturn=1
abs_subturn=1
postsubturn=1
setup=True
until_end=0

When a card is placed during the setup phase:
    abs_subturn += 1
    if abs_subturn == 4 or no more cards can be placed:
        setup=False
        subturn=1
        abs_subturn=0

Then,
On mob move or item use:
    if until_end is 0:
        if not post turn (if postsubturn == 1) and not setup:
            abs_subturn += 1

        if abs_subturn == 3:
            postsubturn += 1 (now it is 2)

    else:
        until-end -= 1

Then,
if post turn (postsubturn >= 2):
    activate each card's post turn abilities in sequence

if every card has been covered (postsubturn >= 5):
    subturn = 1
    abs_subturn = 0
    postsubturn = 1
    turn += 1
```


# Problem-solving space