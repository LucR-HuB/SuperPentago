from uuid import uuid4
from typing import Dict, Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pentago.game import Game
from pentago.board import Quadrant, Direction, Player
from pentago.ai.minimax import best_move

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

games: Dict[str, Game] = {}

COLS = "ABCDEF"
ROWS = "123456"
QMAP = {"Q00": Quadrant.Q00, "Q01": Quadrant.Q01, "Q10": Quadrant.Q10, "Q11": Quadrant.Q11}
DMAP = {"CW": Direction.CW, "CCW": Direction.CCW}

class NewGameResponse(BaseModel):
    game_id: str
    state: dict

class MoveRequest(BaseModel):
    cell: str
    quadrant: str
    direction: str

class BotRequest(BaseModel):
    depth: int = 3
    time_ms: Optional[int] = None

class StateResponse(BaseModel):
    state: dict

class BotMoveResponse(BaseModel):
    state: dict
    move: str

def serialize(g: Game) -> dict:
    w = g.winner()
    return {
        "grid": [row[:] for row in g.board.grid],
        "to_move": "B" if g.current_player() == Player.BLACK else "W",
        "terminal": g.terminal(),
        "winner": "B" if w == Player.BLACK else ("W" if w == Player.WHITE else None),
    }

def parse_cell(cell: str) -> tuple[int, int]:
    s = cell.strip().upper()
    if len(s) != 2 or s[0] not in COLS or s[1] not in ROWS:
        raise ValueError("cell")
    c = COLS.index(s[0])
    r = ROWS.index(s[1])
    return r, c

def move_to_str(r: int, c: int, q: Quadrant, d: Direction) -> str:
    cell = f"{COLS[c]}{ROWS[r]}"
    qname = {Quadrant.Q00: "Q00", Quadrant.Q01: "Q01", Quadrant.Q10: "Q10", Quadrant.Q11: "Q11"}[q]
    dname = "CW" if d == Direction.CW else "CCW"
    return f"{cell} {qname} {dname}"

@app.post("/new", response_model=NewGameResponse)
def new_game():
    gid = uuid4().hex
    g = Game()
    games[gid] = g
    return {"game_id": gid, "state": serialize(g)}

@app.get("/state/{game_id}", response_model=StateResponse)
def get_state(game_id: str):
    g = games.get(game_id)
    if not g:
        raise HTTPException(status_code=404, detail="not found")
    return {"state": serialize(g)}

@app.post("/play/{game_id}", response_model=StateResponse)
def play_move(game_id: str, req: MoveRequest):
    g = games.get(game_id)
    if not g:
        raise HTTPException(status_code=404, detail="not found")
    try:
        r, c = parse_cell(req.cell)
        q = QMAP[req.quadrant.upper()]
        d = DMAP[req.direction.upper()]
        g.play(r, c, q, d)
    except Exception:
        raise HTTPException(status_code=400, detail="illegal move")
    return {"state": serialize(g)}

@app.post("/bot/{game_id}", response_model=BotMoveResponse)
def bot_move(game_id: str, req: BotRequest):
    g = games.get(game_id)
    if not g:
        raise HTTPException(status_code=404, detail="not found")
    if g.terminal():
        return {"state": serialize(g), "move": ""}
    mv = best_move(g.board, g.current_player(), max_depth=req.depth, time_ms=req.time_ms)
    r, c, q, d = mv
    g.play(r, c, q, d)
    return {"state": serialize(g), "move": move_to_str(r, c, q, d)}