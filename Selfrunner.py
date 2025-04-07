import os
from contextlib import chdir

with chdir(os.path.dirname(os.path.realpath(__file__))):
    os.system("python3 Minecards.py")