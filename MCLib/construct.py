import const as c
import argparse as ap

SPRITE_DIM=(384, 576)
CUT_DIM=(230,230)

parser=ap.ArgumentParser(epilog="Et voila! That's how you make a new card.")
parser.add_argument("sprite_path", required=True, help="The path to the card's image.")

args=parser.parse_args()