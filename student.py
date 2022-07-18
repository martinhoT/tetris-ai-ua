# Filipe Gonçalves, 98083
# Pedro Figueiredo, 97487
# Martinho Tavares, 98262


# Projeto disctutido com:
# Rodrigo Lima
# Pedro Lopes
# João Borges
# Gonçalo Machado
# Vicente Costa

import asyncio
import getpass
import json
import os
import time as tm

import websockets
OUT = os.environ.get("OUT", None)

from tree_search import SearchTree, SearchProblem, TetrisDomain
from bot import Bot, Piece, Game, TetrisObject, TetrisState

import logging

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger('websockets').setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from time import time

## GLOBAL VARIABLES
# mudar aqui
HOLES = int(os.environ.get("HOLES", "-1"))
MAX_HEIGHT = int(os.environ.get("MAX_HEIGHT", "-1"))
AVG_HEIGHT = int(os.environ.get("AVG_HEIGHT", "-1"))
HEIGHT_VARIANCE = int(os.environ.get("HEIGHT_VARIANCE", "-1"))
CLEARED_LINES = int(os.environ.get("CLEARED_LINES", "-1"))
CONTINUITY = int(os.environ.get("CONTINUITY", "-1"))
CENTER_SCALE = int(os.environ.get("CENTER_SCALE", "-1"))
HOLES_SCALE = int(os.environ.get("HOLES_SCALE", "-1"))
CLEARED_LINES_SCALE = int(os.environ.get("CLEARED_LINES_SCALE", "-1"))

async def agent_loop(server_address="localhost:8000", agent_name="student"):
    async with websockets.connect(f"ws://{server_address}/player") as websocket:

        # Receive information about static game properties
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name}))

        # number of the piece for curiosity
        piece_n = 1
        # state of the game
        state = None
        # previous 'game' grid from state (ensures we are searching in brand new games, the server may send packets with unfinished moves for some reason)
        prev_game = None
        # tetris domain
        tetris = None
        if HOLES==-1 or MAX_HEIGHT==-1 or AVG_HEIGHT==-1 or HEIGHT_VARIANCE==-1 or CLEARED_LINES==-1 or CONTINUITY==-1 or CENTER_SCALE==-1 or HOLES_SCALE==-1 or CLEARED_LINES_SCALE==-1:
            tetris = TetrisDomain()
        else:
            tetris = TetrisDomain(
                HOLES=HOLES,
                MAX_HEIGHT=MAX_HEIGHT,
                AVG_HEIGHT=AVG_HEIGHT,
                HEIGHT_VARIANCE=HEIGHT_VARIANCE,
                CLEARED_LINES=CLEARED_LINES,
                CONTINUITY=CONTINUITY,
                CENTER_SCALE=CENTER_SCALE,
                HOLES_SCALE=HOLES_SCALE,
                CLEARED_LINES_SCALE=CLEARED_LINES_SCALE)
        # actions list, used with lookahead
        actions = []
        # performance limits for the tree search, which will be reduced when the algorithm becomes too slow to keep up
        # each limit is applied to the respective depth level (from 0 to 3)
        # the limit (length of performance_caps) can't be greater than 4 (yet), since the pieces are unknown beyond that point (may be possible with FLEX_PIECE from TetrisDomain, but it's not implemented yet)
        performance_caps = [3, 3, 3, 3]
        perf = len(performance_caps)
        while True:
            try:
                state = json.loads(
                    await websocket.recv()
                )  # receive game update, this must be called timely or your game will get out of sync with the server

                # AI Implementation
                key = ''
                # if the moving path of the piece has been generated
                # recieve first message
                if "piece" not in state.keys():
                    logger.info("Score: {}".format(state["score"]))
                    # save dimensions
                    dims = state["dimensions"]
                    Bot.update_dimensions(dims[0], dims[1])
                    # do nothing more
                    continue

                # changing pieces
                if not state["piece"]:
                    logger.debug("Piece N: %s", piece_n)
                    piece_n += 1

                # if the decided move hasnt been made yet
                elif prev_game is None or prev_game != state["game"]:
                    prev_game = state["game"]

                    tstate = TetrisState.fromstate(state)

                    # Populate rotations first
                    abnormal = False
                    curr_piece = None if not Bot.contains_rotation(tstate.piece) else tstate.piece
                    while curr_piece is None or tstate.piece!=curr_piece:
                        Bot.register_rotation(tstate.piece, state["piece"])

                        key = 'w'
                        if prev_game != state["game"]:
                            break
                        await websocket.send(
                            json.dumps({"cmd": "key", "key": key})
                        )
                        
                        await asyncio.sleep(1/(state["game_speed"]-1))
                        
                        state = json.loads(
                            await websocket.recv()
                        )
                        if not state["piece"]:
                            abnormal = True
                            break
                        curr_piece = Piece.fromstate(state["piece"])

                    # On extremelly rare occasions, state["piece"] may be None in the previous loop
                    if abnormal:
                        continue

                    logger.debug("Rotations for %s: %s", tstate.piece, Bot.get_rotations(tstate.piece))

                    # Comment to reuse already calculated actions (will be less optimal, but less intensive)
                    if not actions:
                        time = tm.time()
                        # The goal is the same because of how a node satisfies the goal condition in TetrisDomain, at the moment.
                        # Currently, we simply want the solution to be a state such that its size is smaller than the initial state (lower number of lines).
                        tgoal = TetrisState.fromstate(state)
                        problem = SearchProblem(tetris, tstate, tgoal)
                        # The time cap means that the search can take at most 3 frames to complete
                        t = SearchTree(problem, pcaps=performance_caps, time_cap=3/(state["game_speed"]))
                        
                        t.search()

                        logger.debug("Plan: %s", t.plan)
                        logger.debug("Average branching: %s", t.avg_branching)

                        node_final = t.solution
                        logger.debug("Cost: %s", node_final.cost)
                        logger.debug("Heuristic: %s", node_final.heuristic)
                        actions = t.plan
                        time = tm.time() - time

                    max_height = min(j[1] for j in state["game"]) if state["game"] != [] else 0 

                    tempo = time*state["game_speed"]
                    # print(time)
                    if tempo+25 < max_height:
                        if performance_caps[-1] < 3:
                            performance_caps[-1] += 1
                            # print("adding performance -> {}".format(performance_caps))
                        else:
                            if len(performance_caps) < perf:
                                performance_caps.append(1)
                    elif tempo+8 > max_height:
                        if performance_caps[-1] > 1:
                            performance_caps[-1] -= 1
                            # print("subtrating performance -> {}".format(performance_caps))
                        else:
                            if len(performance_caps) > 1: 
                                performance_caps.pop()
                    time = 0

                    action_r, action_t = actions.pop(0)
                    
                    decided_move_path = ['w']*action_r + (['a'] if action_t < 0 else ['d'])*abs(action_t)# + ['s']
                    if state["game_speed"] < 130:
                        decided_move_path.append('s')
                    logger.debug("Rotations: %s",action_r)
                    logger.debug("Translations: %s",action_t)
                    logger.debug("Decided move path: %s",decided_move_path)

                    for key in decided_move_path:
                        prev_piece = state["piece"]
                        if prev_game != state["game"]:
                            break
                        await websocket.send(
                            json.dumps({"cmd": "key", "key": key})
                        )
                        await asyncio.sleep(1/state["game_speed"])
                        # Sometimes the 'game.py' is not fast enough to register all inputs, we want to make sure it does register them all
                        while Bot.no_action(prev_piece, state["piece"]):
                            state = json.loads(
                                    await websocket.recv()
                            )

                            if not state["piece"]:
                                break

            except websockets.exceptions.ConnectionClosedOK:
                
                logger.debug("Server has cleanly disconnected us")
                if OUT:
                    f = open(OUT, 'w')
                    f.write(str(state["score"]))
                    f.close()
                logger.info("""
                Cache sizes:
                    Cached games clears: %s
                    Cached games clears hits: %s
                    Cached actions: %s
                    Cached actions hits: %s
                    Cached heuristic: %s
                    Cached heuristic hits: %s
                Bank sizes:
                    TetrisObject bank pos: %s
                    Game bank pos: %s
                    Game bank sqs: %s
                    Game bank lines: %s
                    Piece bank pos: %s
                    Piece bank sqs: %s
                    Piece bank lines: %s
                    Piece bank falls: %s
                """,
                    len(tetris.cached_games_clears),
                    tetris.stats["cached_games_clears_hits"],
                    len(tetris.cached_actions),
                    tetris.stats["cached_actions_hits"],
                    len(tetris.cached_heuristic),
                    tetris.stats["cached_heuristic_hits"],
                    len(TetrisObject.bank_lines_from_pos),
                    len(Game.bank_lines_from_pos),
                    len(Game.bank_game_sqs),
                    len(Game.bank_game_lines),
                    len(Piece.bank_lines_from_pos),
                    len(Piece.bank_piece_sqs),
                    len(Piece.bank_piece_lines),
                    len(Piece.bank_falls))
                return

            # Next line is not needed for AI agent
            # pygame.display.flip()


# DO NOT CHANGE THE LINES BELLOW
# You can change the default values using the command line, example:
# $ NAME='arrumador' python3 client.py
loop = asyncio.get_event_loop()
SERVER = os.environ.get("SERVER", "localhost")
PORT = os.environ.get("PORT", "8000")
NAME = os.environ.get("NAME", getpass.getuser())
loop.run_until_complete(agent_loop(f"{SERVER}:{PORT}", NAME))
