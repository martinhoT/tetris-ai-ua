"""Terminal viewer application."""
import argparse
import asyncio
import json
import os
import requests
import websockets

def getCubes(game):
    cubes = []
    for piece in game:
        cubes += [piece]
    return cubes
	

async def messages_handler(websocket_path, queue):
    """Handles server side messages, putting them into a queue."""
    async with websockets.connect(websocket_path) as websocket:
        await websocket.send(json.dumps({"cmd": "join"}))

        while True:
            update = await websocket.recv()
            queue.put_nowait(update)


async def main_loop(queue):
    """Processes events from server and display's."""

    state = await queue.get()  # first state message includes map information
    newgame_json = json.loads(state)
    player_name = ""


    dimensions = newgame_json["dimensions"]

    grid = newgame_json["grid"]

    game_speed = newgame_json["game_speed"]


    while True:

        try:
            state = json.loads(queue.get_nowait())
            if "score" in state:
                score = state["score"]

            if "player" in state:
                player_name = state["player"]

            if "game_speed" in state:
                game_speed = state["game_speed"]

            if "game" in state:
                game = state["game"]

            if "piece" in state:
                piece = state["piece"]

            if game and piece:
                pieces = getCubes(game + piece)
                #print(pieces)

                middle = int((len(str(dimensions[1])) + 1 + dimensions[0])/2) - 3
                board =  " "*middle + "TETRIS\n"
                # Print board
                for y in range(1,dimensions[1]):
                    layer = "0"*(len(str(dimensions[1])) - len(str(y))) + f"{y} "
                    board += layer
                    for x in range(1,dimensions[0] - 1):
                        if [x,y] in pieces:
                            board += "□"
                        else:
                            board += "■"
                    board += "\n"
                
                # Add status
                board += f"\nSPEED: {game_speed}\nSCORE: {score}\n\n\n\n"
                print(board, end="\r", flush=True)

        except asyncio.queues.QueueEmpty:
            await asyncio.sleep(1.0 / game_speed)
            continue


if __name__ == "__main__":
    SERVER = os.environ.get("SERVER", "localhost")
    PORT = os.environ.get("PORT", "8000")

    parser = argparse.ArgumentParser()
    parser.add_argument("--server", help="IP address of the server", default=SERVER)
    parser.add_argument(
        "--scale", help="reduce size of window by x times", type=int, default=1
    )
    parser.add_argument("--port", help="TCP port", type=int, default=PORT)

    arguments = parser.parse_args()
    SCALE = arguments.scale

    LOOP = asyncio.get_event_loop()
    q = asyncio.Queue()

    ws_path = f"ws://{arguments.server}:{arguments.port}/viewer"

    try:
        LOOP.run_until_complete(
            asyncio.gather(messages_handler(ws_path, q), main_loop(q))
        )
    except RuntimeError as err:
        pass
    finally:
        LOOP.stop()