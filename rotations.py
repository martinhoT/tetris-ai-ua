# Filipe Gonçalves, 98083
# Pedro Figueiredo, 97487
# Martinho Tavares, 98262

from shape import SHAPES
from bot import Bot

x = 10
piece_x = 5

def rotations(shape):
    res = []
    for i in range(4):
        if shape.positions not in res:
            res.append(shape.positions)
        shape.rotate()
    return res

for s in SHAPES:
    s.set_pos((x-piece_x)/2,1)

known_rotations = { str( Bot.normalPos({(x,y) for x,y in s.positions})[0] ): [ { (x,y) for x,y in rot } for rot in rotations(s) ] for s in SHAPES }
for piece, rotation_lst in known_rotations.items():
    print('\'{0}\': {1},'.format(piece, rotation_lst))
