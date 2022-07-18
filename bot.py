# Filipe Gonçalves, 98083
# Pedro Figueiredo, 97487
# Martinho Tavares, 98262

from typing import List, Tuple

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)

"""
Assumptions:
- The pieces, when entering the grid, don't spawn in different places (would complicate Bot.known_rotations)
"""

class Bot:
    """
Class with helper methods for the AI.
Also includes caching and maintaining of important values for the necessary operations (such as grid size).
    """

    # dimensions of the game
    dimensions = [None, None]
    full_line = None

    known_rotations = {}

    @classmethod
    def update_dimensions(cls, x: int, y: int):
        cls.dimensions = [x, y]
        cls.full_line = 2**(x-2)-1

    @classmethod
    def register_rotation(cls, piece: 'Piece', rotation: List[List[int]]):
        pos = cls.top_left(rotation)
        Bot.known_rotations.setdefault(piece, []).append( (Piece.fromstate(rotation), pos) )
    
    @classmethod
    def get_rotations(cls, piece: 'Piece') -> Tuple['Piece', Tuple[int]]:
        return Bot.known_rotations[piece]

    @classmethod
    def contains_rotation(cls, piece: 'Piece') -> bool:
        return piece in cls.known_rotations

    @classmethod
    def x(cls) -> int:
        return cls.dimensions[0]

    @classmethod
    def y(cls) -> int:
        return cls.dimensions[1]

    @classmethod
    def no_action(cls, piece_a: List[List[int]], piece_b: List[List[int]]) -> bool:
        """
Checks if piece_a is not simply a product of piece_b falling.\n
Used to check if an action has been performed on a piece.
If no action has been performed, the method returns True.\n
Both pieces should have the same length (it only makes sense if both are the same "piece" anyway).\n
The pieces are lists of positions, not Piece objects. This function is intended to be used with the raw state data from the server (less overhead).
        """

        fall_height = abs(piece_a[0][1]-piece_b[0][1])
        for idx in range(1,len(piece_a)):
            xa, ya = piece_a[idx]
            xb, yb = piece_b[idx]
            if abs(ya-yb) != fall_height or xa!=xb:
                return False
        return piece_a[0][0]==piece_b[0][0]
    
    @classmethod
    def top_left(cls, piece: List[List[int]]):
        minx = Bot.x()
        miny = Bot.y()
        for x,y in piece:
            minx = x if x < minx else minx
            miny = y if y < miny else miny
        
        return (minx, miny)



class TetrisState:
    """Simple wrapper class for a structure of different TetrisObject instances."""

    def __init__(self, game: 'Game', piece: 'Piece', next_pieces: List['Piece']):
        self.game = game
        self.piece = piece
        self.next_pieces = next_pieces

    @classmethod
    # Builder method    
    def fromstate(cls, state: dict):
        """'state' is the dictionary that is provided by the server"""
        return TetrisState(
            Game.fromstate( state["game"] ),
            Piece.fromstate( state["piece"] ),
            [ Piece.fromstate(n) for n in state["next_pieces"] ])

    def __str__(self):
        return "Game: {0}\nPiece: {1}\nNext pieces: {2}".format(self.game, self.piece, self.next_pieces)



class TetrisObject:

    # Save results of lines_from_pos
    bank_lines_from_pos = {}

    def __init__(self, lines: Tuple[int]=None, width: int=None):
        self.lines = lines
        self.width = width
        self._heights = None

    @classmethod
    def lines_from_pos(cls, sqs: List[List[int]], width: int=None):
        """
Returns a list of integers, where each is the binary representation of the rows in 'sqs'.
- 'sqs' is a list of occupied positions.
- 'width' is the width of the object (for example, the Game has width equal to that of the grid, while Piece uses its own width).
        """
        key = str(sqs) + str(width)
        if key in cls.bank_lines_from_pos:
            return cls.bank_lines_from_pos[key]
        
        h = {}
        maxx = 0
        for x,y in sqs:
            h.setdefault(y, []).append(x)
            maxx = x if x > maxx else maxx
    
        width = width if width else maxx
        res = tuple( sum(2**(width-x) for x in l) for _,l in sorted(h.items()) )
        cls.bank_lines_from_pos[key] = res
        return res

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, TetrisObject) and self.lines==__o.lines

    def __hash__(self) -> int:
        return hash(self.lines)
    
    def __bool__(self) -> bool:
        return bool(self.lines)

    def binary(self, i: int) -> str:
        """Return the binary representation of a line in this TetrisObject."""
        return bin(i)[2:].zfill( self.width )

    def binary_ones_pos(self, num: int) -> List[int]:
        """Return the indexes of the set bits (ones) in the binary representation of a line in this TetrisObject."""
        return [ idx for idx, bit in enumerate( self.binary(num) ) if bit=='1' ]

    def heights(self, base: int=None, offset: int=0) -> List[List[int]]:
        """Return a list of heights for each X in self.lines."""
        if not self._heights:
            self._heights = []
            for _ in range(self.width):
                self._heights.append( [base] if base else [] )
            for height in range(self.size()):
                filled_squares_indexes = self.binary_ones_pos(self.lines[height])
                for square_idx in filled_squares_indexes:
                    self._heights[square_idx].append(height+offset)
            self._heights = [ sorted(h, reverse=True) for h in self._heights ]
        return self._heights

    def size(self) -> int:
        return len(self.lines)
    
    def __str__(self) -> str:
        return ''.join([ '\n' + self.binary(l).replace('0','.').replace('1', '█') for l in self.lines ])

    def __repr__(self) -> str:
        return str(self)



class Game(TetrisObject):

    bank_game_sqs = {}
    bank_game_lines = {}

    def __init__(self, lines: Tuple[int]=None):
        super().__init__(lines, Bot.x()-2)
        self._head = None
        self._clear = None

    """
Builder methods.
Equal games may be created from scratch many times, and their respective
operations may be repeated as well. This controls object instantiation,
in order to recycle references.
    """
    @classmethod
    def fromstate(cls, sqs: List[List[int]]):
        key = str(sqs)
        if key in cls.bank_game_sqs:
            return cls.bank_game_sqs[key]
        
        lines = cls.lines_from_pos(sqs, Bot.x()-2)
        res = Game( lines )
        cls.bank_game_sqs[key] = res
        cls.bank_game_lines[lines] = res
        return res
    @classmethod
    def fromlines(cls, lines: Tuple[int]):
        key = lines
        if key in cls.bank_game_lines:
            return cls.bank_game_lines[key]
        
        res = Game( lines )
        cls.bank_game_lines[key] = res
        return res

    def heights(self) -> List[List[int]]:
        return super().heights( Bot.y(), Bot.y()-self.size() )

    def clear(self) -> Tuple['Game', List[int]]:
        """
Clear the complete horizontal rows out of the grid.
Return the resulting Game and a list of each clearing instance, representing the number of rows cleared in that same instance.
        """

        if not self._clear:
            newlines = tuple(l for l in self.lines if l!=Bot.full_line)
            self._clear = (Game.fromlines( newlines ), self.size() - len(newlines))

        return self._clear

class Piece(TetrisObject):

    bank_piece_sqs = {}
    bank_piece_lines = {}
    bank_falls = {}

    def __init__(self, lines: Tuple[int]=None):
        super().__init__(lines, max(len(bin(l))-2 for l in lines) if lines else None)
 
    """
These methods serve the same purpose as the ones in Game.
They recycle object instances in order to prevent repeated operations.
    """
    @classmethod
    def fromstate(cls, sqs: List[List[int]]):
        key = str(sqs)
        if key in cls.bank_piece_sqs:
            return cls.bank_piece_sqs[key]

        lines = cls.lines_from_pos(sqs)
        res = Piece( lines )
        cls.bank_piece_sqs[key] = res
        cls.bank_piece_lines[lines] = res
        return res
    @classmethod
    def fromlines(cls, lines: Tuple[int]):
        key = lines
        if key in cls.bank_piece_lines:
            return cls.bank_piece_lines[key]
        
        res = Piece( lines )
        cls.bank_piece_lines[key] = res
        return res

    def fall(self, game: Game, r: int, t: int) -> Game:
        key = (self, game, r, t)
        if key in Piece.bank_falls:
            return Piece.bank_falls[key]

        # Do the rotation and the translation
        piece, pos = Bot.get_rotations(self)[r]
        pos = (pos[0]+t, pos[1])

        top_heights = [ h[-1] for h in game.heights()[pos[0]-1:pos[0]+piece.width-1] ]
        bot_heights = [ h[0] for h in piece.heights() ]
        fall_height = min(top-bot for top, bot in zip(top_heights, bot_heights))
        height_idx = Bot.y() - (fall_height + piece.size()) + 1
        newlines = list(game.lines)

        shifted_lines_idx = 0
        shifted_lines = tuple( l<<(game.width - piece.width - pos[0] + 1) for l in piece.lines )

        for line_idx in range(height_idx, game.size()):
            newlines[-line_idx-1] |= shifted_lines[-shifted_lines_idx-1]
            shifted_lines_idx += 1
            if not shifted_lines_idx < piece.size():
                break
        for line_idx in range(shifted_lines_idx, piece.size()):
            newlines[:0] = [shifted_lines[-line_idx-1]]

        res = Game.fromlines( tuple(newlines) )
        Piece.bank_falls[key] = res
        return res
