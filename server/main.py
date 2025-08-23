from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
from uuid import uuid4
import time

from pentago.game import Game
from pentago.board import Player, Quadrant, Direction
from pentago.ai.minimax import best_move as best_move_minimax
from pentago.ai.mcts import best_move_mcts, mcts_reset, mcts_rebase

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GAMES: Dict[str, Game] = {}
PROGRESS: Dict[str, dict] = {}

class PlayRequest(BaseModel):
    cell: str
    quadrant: str
    direction: str

class BotRequest(BaseModel):
    depth: int
    time_ms: Optional[int] = None
    engine: Optional[str] = "minimax"
    simulations: Optional[int] = None

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

@app.post("/new")
def new_game():
    g = Game()
    gid = uuid4().hex
    GAMES[gid] = g
    mcts_reset()
    PROGRESS.pop(gid, None)
    return {"game_id": gid, "state": to_state(g)}

@app.get("/state/{gid}")
def state(gid: str):
    g = GAMES.get(gid)
    if g is None:
        raise HTTPException(404, "unknown game")
    return {"state": to_state(g)}

@app.get("/progress/{gid}")
def progress(gid: str):
    p = PROGRESS.get(gid)
    if not p:
        return {"engine": None, "done": True}
    out = dict(p)
    elapsed_ms = out.get("elapsed_override_ms")
    if elapsed_ms is None:
        elapsed_ms = int((time.time() - p["start_ts"]) * 1000)
    out["elapsed_ms"] = int(elapsed_ms)
    percent = None
    if p.get("time_ms"):
        tm = p["time_ms"]
        if tm and tm > 0:
            percent = min(1.0, out["elapsed_ms"] / tm)
    if percent is None and p.get("sims_target"):
        target = p["sims_target"]
        done = p.get("sims_done", 0)
        if target and target > 0:
            percent = min(1.0, done / target)
    out["percent"] = percent
    return out

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
    mcts_rebase(g.board, g.current_player(), prune=True)
    return {"state": to_state(g)}

@app.post("/bot/{gid}")
def bot(gid: str, req: BotRequest):
    g = GAMES.get(gid)
    if g is None:
        raise HTTPException(404, "unknown game")
    engine = (req.engine or "minimax").lower()
    side = g.current_player()

    PROGRESS[gid] = {
        "engine": engine,
        "done": False,
        "start_ts": time.time(),
        "time_ms": req.time_ms,
        "sims_target": None,
        "sims_done": 0,
    }

    if engine == "minimax":
        def _cb_ms(elapsed_ms: int):
            PROGRESS[gid]["elapsed_override_ms"] = int(elapsed_ms)
        r, c, q, d = best_move_minimax(
            g.board,
            player_to_move=side,
            max_depth=req.depth,
            time_ms=req.time_ms,
            progress_cb=_cb_ms,
        )

    elif engine == "mcts":
        mcts_rebase(g.board, side, prune=False)
        if req.time_ms is not None:
            sims = None
        else:
            if req.simulations is not None:
                sims = max(1, int(req.simulations))
            else:
                sims = max(200, req.depth * 500)
        PROGRESS[gid]["sims_target"] = sims
        def _cb(done_sims: int):
            PROGRESS[gid]["sims_done"] = done_sims
        r, c, q, d = best_move_mcts(
            g.board,
            player_to_move=side,
            time_ms=req.time_ms,
            simulations=sims,
            progress_cb=_cb,
        )
    else:
        raise HTTPException(400, "engine not implemented")

    PROGRESS[gid]["done"] = True

    g.play(r, c, q, d)
    mcts_rebase(g.board, g.current_player(), prune=True)
    cell = f"{COLS[c]}{ROWS[r]}"
    move_str = f"{cell} {q.name} {d.name}"
    return {"move": move_str, "state": to_state(g), "engine": engine}