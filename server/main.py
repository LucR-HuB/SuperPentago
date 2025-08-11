from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
from uuid import uuid4

from pentago.game import Game
from pentago.board import Player
from pentago.ai.minimax import best_move as minimax_best
from pentago.ai.mcts import best_move_mcts as mcts_best

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GAMES: Dict[str, Game] = {}

class PlayRequest(BaseModel):
    cell: str
    quadrant: str
    direction: str

class BotRequest(BaseModel):
    depth: int
    time_ms: Optional[int] = None
    engine: Optional[str] = "minimax"

COLS = "ABCDEF"
ROWS = "123456"

def to_state(g: Game) -> dict:
    grid = [row[:] for row in g.board.grid]
    to_move = "B" if g.current_player() == Player.BLACK else "W"
    term = g.terminal()
    win = g.winner()
    winner = ("B" if win == Player.BLACK else "W") if win is not None else None
    return {"grid": grid, "to_move": to_move, "terminal": term, "winner": winner}

def parse_cell(cell: str) -> tuple[int, int]:
    s = cell.strip().upper()
    if len(s) != 2 or s[0] not in COLS or s[1] not in ROWS:
        raise ValueError("invalid cell")
    c = COLS.index(s[0])
    r = ROWS.index(s[1])
    return r, c

def parse_play(req: PlayRequest) -> tuple[int, int, str, str]:
    r, c = parse_cell(req.cell)
    q = req.quadrant.upper()
    d = req.direction.upper()
    if q not in {"Q00", "Q01", "Q10", "Q11"}:
        raise ValueError("invalid quadrant")
    if d not in {"CW", "CCW"}:
        raise ValueError("invalid direction")
    return r, c, q, d

@app.post("/new")
def new_game():
    g = Game()
    gid = uuid4().hex
    GAMES[gid] = g
    return {"game_id": gid, "state": to_state(g)}

@app.get("/state/{gid}")
def state(gid: str):
    g = GAMES.get(gid)
    if g is None:
        raise HTTPException(404, "unknown game")
    return {"state": to_state(g)}

@app.post("/play/{gid}")
def play(gid: str, req: PlayRequest):
    g = GAMES.get(gid)
    if g is None:
        raise HTTPException(404, "unknown game")
    try:
        r, c, q, d = parse_play(req)
        qmap = {"Q00": 0, "Q01": 1, "Q10": 2, "Q11": 3}
        dmap = {"CW": 1, "CCW": -1}
        from pentago.board import Quadrant, Direction
        g.play(r, c, Quadrant(qmap[q]), Direction(dmap[d]))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"state": to_state(g)}

@app.post("/bot/{gid}")
def bot(gid: str, req: BotRequest):
    g = GAMES.get(gid)
    if g is None:
        raise HTTPException(404, "unknown game")
    engine = (req.engine or "minimax").lower()
    side = g.current_player()
    if engine == "minimax":
        r, c, q, d = minimax_best(g.board, player_to_move=side, max_depth=req.depth, time_ms=req.time_ms)
    elif engine == "mcts":
        r, c, q, d = mcts_best(g.board, player_to_move=side, time_ms=req.time_ms)
    else:
        raise HTTPException(400, "engine not implemented")

    cell = f"{COLS[c]}{ROWS[r]}"
    move_str = f"{cell} {q.name} {d.name}"
    g.play(r, c, q, d)
    return {"move": move_str, "state": to_state(g), "engine": engine}