from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
from uuid import uuid4

from pentago.game import Game
from pentago.board import Player, Quadrant, Direction
from pentago.ai.minimax import best_move

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
QMAP_STR_TO_ENUM = {"Q00": Quadrant.Q00, "Q01": Quadrant.Q01, "Q10": Quadrant.Q10, "Q11": Quadrant.Q11}
DMAP_STR_TO_ENUM = {"CW": Direction.CW, "CCW": Direction.CCW}

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

def parse_play(req: PlayRequest) -> tuple[int, int, Quadrant, Direction]:
    r, c = parse_cell(req.cell)
    q = QMAP_STR_TO_ENUM.get(req.quadrant.upper())
    d = DMAP_STR_TO_ENUM.get(req.direction.upper())
    if q is None:
        raise ValueError("invalid quadrant")
    if d is None:
        raise ValueError("invalid direction")
    return r, c, q, d

# ---- Endpoints ----
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
        g.play(r, c, q, d)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"state": to_state(g)}

@app.post("/bot/{gid}")
def bot(gid: str, req: BotRequest):
    g = GAMES.get(gid)
    if g is None:
        raise HTTPException(404, "unknown game")
    engine = (req.engine or "minimax").lower()
    if engine != "minimax":
        raise HTTPException(400, "engine not implemented yet")

    side = g.current_player()
    r, c, q, d = best_move(g.board, player_to_move=side, max_depth=req.depth, time_ms=req.time_ms)
    g.play(r, c, q, d)

    cell = f"{COLS[c]}{ROWS[r]}"
    move_str = f"{cell} {q.name} {d.name}"
    return {"move": move_str, "state": to_state(g), "engine": engine}