# Filipe Gonçalves, 98083
# Pedro Figueiredo, 97487
# Martinho Tavares, 98262

# The Search classes have been repurposed from the second practical assignment, about tree search: https://github.com/detiuaveiro/iia-ia-guiao-pesquisa

from typing import List, Tuple

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)

from time import time

from bot import Bot, TetrisState, Piece

# General lambda functions
avg = lambda l: sum(l)/len(l)
variance = lambda l: sum( [(x-avg(l))**2 for x in l] )/(len(l)-1) if len(l)>1 else 0

class TetrisDomain:

    """
    - state: an instance of TetrisState, with an instance of Game, Piece and list of next Pieces.
    - action: tuple of two integer values, where the first one specifies the number of rotations and the second one specifies how many translation actions along the X axis have to be done to arrive at the final position (with left-to-right being positive, and the reverse negative).
    - goal: different variations of the goal state exist:
        - a state where the "game" is equal to the goal's "game" (which, usually, should be a completelly empty game);
        - the "game" has to be smaller in size than the goal's "game", implying that blind scoring should be the priority;
        - (current) the goal's height should always be 4 or less. If it's too high (greater than 8) then simply try to score. Only count as a solution if the whole lookahead/max_depth has been traversed.

    The cost indicates how much effort will the bot do to achieve the goal.
    Each action will simply cost 17, and if scoring happens then the score will be subtracted from this cost.
    """

    def __init__(self,
        HOLES=24864,
        MAX_HEIGHT=10858,
        AVG_HEIGHT=28652,
        HEIGHT_VARIANCE=1604,
        CLEARED_LINES=1659,
        CONTINUITY=15965,
        CENTER_SCALE=13238,
        HOLES_SCALE=22233,
        CLEARED_LINES_SCALE=12438):

        # Heuristic parameters
        self.HOLES = HOLES
        self.MAX_HEIGHT = MAX_HEIGHT
        self.AVG_HEIGHT = AVG_HEIGHT
        self.HEIGHT_VARIANCE = HEIGHT_VARIANCE
        self.CLEARED_LINES = CLEARED_LINES
        self.CONTINUITY = CONTINUITY
        # The scales should ideally be up to 32768
        self.CENTER_SCALE = CENTER_SCALE/16384
        self.HOLES_SCALE = HOLES_SCALE/16384
        self.CLEARED_LINES_SCALE = CLEARED_LINES_SCALE/16384
        
        # Function that gives greater weight to central columns the greater the value of CENTER_SCALE (and vice-versa)
        # 'mx' is the maximum value on X that the function takes (between 0 and X)
        self.center_weight = lambda mx: [ (2-self.CENTER_SCALE) * -( (x-mx/2)**2 )/( (mx/2)**2 ) + 1 for x in range(mx) ]

        # Piece that represents any piece (for lookahead of unknown pieces). It's equal to a null Piece, a Piece instance 'p' where bool(p)==False
        self.FLEX_PIECE = Piece()
        # Dictionary that functions as a cache, saves the resulting game from an unscored game (with lines to be cleared) and how much score it provides.
        self.cached_games_clears = {}
        # Save the possible actions for a piece
        self.cached_actions = {}
        # Save the values for the heuristic given a game
        self.cached_heuristic = {}
        # Stats for analysis
        self.stats = {
            "cached_games_clears_hits": 0,
            "cached_actions_hits": 0,
            "cached_heuristic_hits": 0
        }

    def actions(self, state: TetrisState):
        piece = state.piece

        if piece in self.cached_actions:
            self.stats["cached_actions_hits"] += 1
            return self.cached_actions[piece]

        if not Bot.contains_rotation(piece):
            return []

        actions = []
        r = 0
        for rotation, pos in Bot.get_rotations(piece):
            actions.extend([ (r,t-pos[0]) for t in range(1, Bot.x()-rotation.width) ])
            r += 1

        self.cached_actions[piece] = actions
        return actions

    def result(self, state: TetrisState, action):
        game_before = state.piece.fall(state.game, action[0], action[1])
        
        if game_before not in self.cached_games_clears:
            game_final, clears = game_before.clear()
            self.cached_games_clears[game_before] = (game_final, clears**2)
        else:
            self.stats["cached_games_clears_hits"] += 1
            game_final = self.cached_games_clears[game_before][0]

        next_pieces = state.next_pieces
        return TetrisState(game_final, next_pieces[0] if next_pieces else self.FLEX_PIECE, next_pieces[1:])

    # result() should be executed first (because the cache is used here, which is filled in result())
    def cost(self, state: TetrisState, action):
        return 17 - self.cached_games_clears[ state.piece.fall(state.game, action[0], action[1]) ][1]

    # heuristic for the game
    def heuristic(self, state: TetrisState, goal: TetrisState):
        if state.game in self.cached_heuristic:
            self.stats["cached_heuristic_hits"] += 1
            return self.cached_heuristic[state.game]
        
        heights = state.game.heights()
        top_heights = [h[-1] for h in heights]

        weighted_top_heights = [ h*c for h,c in zip(top_heights, self.center_weight(state.game.width-1)) ]

        # Get the top height
        max_height = min(weighted_top_heights)

        # Get the average height
        avg_height = avg(weighted_top_heights)

        # Obtain the variance of the heights
        height_variance = variance(weighted_top_heights)

        # Get holes (analyzed vertically)
        holes = sum([ (sum([ x for x in self.next_differences(l[::-1]) ])-len(l)+1)**self.HOLES_SCALE for l in heights ])

        # Number of cleared lines
        cleared = (state.game.size()-goal.game.size())
        # Avoid creating a complex number
        cleared = cleared**self.CLEARED_LINES_SCALE if cleared > 0 else -( (-cleared)**2 )

        # Analyze horizontal holes, if there isn't horizontal continuity. The lesser the continuity, the greater this value is
        continuity = sum( len(set(heights[i]).symmetric_difference(set(heights[i+1]))) for i in range(state.game.width-1) )

        heuristic = \
            +holes*self.HOLES \
            +continuity*self.CONTINUITY \
            +cleared*self.CLEARED_LINES \
            +(Bot.y()-max_height)*self.MAX_HEIGHT \
            +(Bot.y()-avg_height)*self.AVG_HEIGHT \
            +height_variance*self.HEIGHT_VARIANCE
        self.cached_heuristic[state.game] = heuristic

        return heuristic

    def satisfies(self, state: TetrisState, goal: TetrisState):
        return len(state.next_pieces) < len(goal.next_pieces) and state.game.size() < goal.game.size()

    @classmethod
    def next_differences(cls, lst):
        return [lst[idx+1]-lst[idx] for idx in range(len(lst)-1)]



class SearchProblem:
    def __init__(self, domain, initial, goal):
        self.domain = domain
        self.initial = initial
        self.goal = goal
    def goal_test(self, state):
        return self.domain.satisfies(state,self.goal)



class SearchNode:
    def __init__(self,state,parent,cost=0,heuristic=0,pre_action=None): 
        self.state = state
        self.parent = parent
        self.depth = 0 if parent is None else parent.depth+1
        self.cost = cost
        self.heuristic = heuristic
        self.pre_action = pre_action

    def __str__(self):
        return "no(" + str(self.state) + "," + str(self.parent) + ")"
    def __repr__(self):
        return str(self)

    def in_parent(self, state):
        if self.parent is None:
            return False
        return True if self.parent.state==state else self.parent.in_parent(state)

    def pre_actions(self):
        return (self.parent.pre_actions() if self.parent else []) + ([self.pre_action] if self.pre_action is not None else [])



class SearchTree:

    def __init__(self,problem,pcaps: List[int] = [5,5,5,5],time_cap: float=1): 
        self.problem = problem
        root = SearchNode(problem.initial, None)
        self.open_nodes = [root]
        self.solution = None
        self.terminals = 0
        self.non_terminals = 0
        self.avg_branching = 0
        self.average_depth = 0
        self.plan = []
        # Top priority to node cost, then to A* cost
        self.node_order = lambda x: (x.cost, x.cost + x.heuristic)
        # In case a solution hasn't been found yet. Only returns this as a solution if 'best_effort' is True
        self.lowest_astar_node = (root, None)
        # The maximum number of nodes that are expanded (prunning), for each depth level
        self.pcaps = pcaps
        self.limit = len(self.pcaps)
        # Set a limit to the time the tree search takes. Once the limit is broken, the result will be best-effort
        self.time_cap = time_cap
        self.time_stats = {
            "result": 0,
            "actions": 0,
            "cost/heuristic": 0,
            "total": 0
        }

    def get_path(self, node):
        if node.parent == None:
            return [node.state]
        path = self.get_path(node.parent)
        path += [node.state]
        return(path)

    def search(self):
        all_depth = [0]
        tt = time()
        while self.open_nodes != []:
            node = self.open_nodes.pop(0)
            if self.problem.goal_test(node.state):
                return self.terminate(node, all_depth, tt)

            self.non_terminals = self.non_terminals + 1

            lnewnodes = []
            if self.limit is not None and node.depth >= self.limit:
                continue

            t = time()
            actions = self.problem.domain.actions(node.state)
            self.time_stats["actions"] += time() - t
            for a in actions:
                t = time()
                newstate = self.problem.domain.result(node.state,a)
                self.time_stats["result"] += time() - t
                if not node.in_parent(newstate):
                    t = time()
                    newnode = SearchNode(newstate,node,
                        node.cost+self.problem.domain.cost(node.state,a),
                        self.problem.domain.heuristic(newstate,self.problem.goal),
                        a)
                    self.time_stats["cost/heuristic"] += time() - t
                    lnewnodes.append(newnode)
                    # Average node depth
                    all_depth.append(newnode.depth)
                    # Lowest cost note
                    if self.lowest_astar_node[1] is None or self.node_order(newnode)[1] < self.lowest_astar_node[1]:
                        self.lowest_astar_node = (newnode, newnode.cost + newnode.heuristic)

            if time() - tt > self.time_cap:
                break
            self.open_nodes.extend(lnewnodes)
            self.open_nodes = sorted(self.open_nodes, key=self.node_order)[:self.pcaps[node.depth]]

        return self.terminate(self.lowest_astar_node[0], all_depth, tt, "BEST EFFORT")

    # Used to terminate a search. Avoids repeated blocks of code (since the search is terminated for different reasons).
    def terminate(self, node, all_depth, tt, method: str="SOLUTION"):
        self.solution = node
        self.terminals = len(self.open_nodes) + 1
        self.avg_branching = round((self.non_terminals + self.terminals - 1)/(self.non_terminals), 2)
        self.average_depth = sum(all_depth)/len(all_depth)
        self.time_stats["total"] += time() - tt
        self.plan = self.solution.pre_actions()

        logger.info("USED %s", method)
        logger.debug("""
        Terminal nodes: %d
        Non terminal nodes: %d
        Average depth: %f
        Average branching: %f
        Times:
            actions - %s
            result  - %s
            cost/heuristic - %s
            total   - %s
        """, self.terminals, self.non_terminals, self.average_depth, self.avg_branching, self.time_stats["actions"], self.time_stats["result"], self.time_stats["cost/heuristic"], self.time_stats["total"])
        return self.get_path(node)

    @property
    def length(self):
        return self.solution.depth if self.solution is not None else None

    @property
    def cost(self):
        return self.solution.cost
