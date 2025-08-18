import time
import math
from typing import List, Tuple, Optional, Dict, Callable
from ..board import Board, Player, Quadrant, Direction

Move = Tuple[int, int, Quadrant, Direction]

TTEntry = Tuple[int, int, int, Optional[Move]]
TT: Dict[Tuple[int, Tuple[int, ...]], TTEntry] = {}

STATS: Dict[str, int] = {
    "nodes": 0,
    "evals": 0,
    "tt_probe": 0,
    "tt_hit": 0,
    "cuts": 0,
    "leaf_terminal": 0,
}

def reset_stats() -> None:
    STATS["nodes"] = 0
    STATS["evals"] = 0
    STATS["tt_probe"] = 0
    STATS["tt_hit"] = 0
    STATS["cuts"] = 0
    STATS["leaf_terminal"] = 0
    TT.clear()

def stats_snapshot() -> Dict[str, int]:
    return dict(STATS)

def opponent(p: Player) -> Player:
    return Player.BLACK if p == Player.WHITE else Player.WHITE

def board_key(board: Board, to_move: Player) -> Tuple[int, Tuple[int, ...]]:
    flat = tuple(v for row in board.grid for v in row)
    return (int(to_move), flat)

def generate_moves(board: Board) -> List[Move]:
    out: List[Move] = []
    for r, c in board.legal_placements():
        out.append((r, c, Quadrant.Q00, Direction.CW))
        out.append((r, c, Quadrant.Q00, Direction.CCW))
        out.append((r, c, Quadrant.Q01, Direction.CW))
        out.append((r, c, Quadrant.Q01, Direction.CCW))
        out.append((r, c, Quadrant.Q10, Direction.CW))
        out.append((r, c, Quadrant.Q10, Direction.CCW))
        out.append((r, c, Quadrant.Q11, Direction.CW))
        out.append((r, c, Quadrant.Q11, Direction.CCW))
    return out

def apply_move(board: Board, player: Player, mv: Move) -> Tuple[Board, Optional[Player], bool]:
    r, c, q, d = mv
    b2 = board.copy()
    b2.place(r, c, player)
    b2.rotate(q, d)
    cur = b2.check_five(player)
    opp = b2.check_five(opponent(player))
    if cur and opp:
        STATS["leaf_terminal"] += 1
        return b2, player, True
    if cur:
        STATS["leaf_terminal"] += 1
        return b2, player, True
    if opp:
        STATS["leaf_terminal"] += 1
        return b2, opponent(player), True
    if b2.full():
        STATS["leaf_terminal"] += 1
        return b2, None, True
    return b2, None, False

CENTER_WEIGHTS = [
    [1, 2, 3, 3, 2, 1],
    [2, 3, 4, 4, 3, 2],
    [3, 4, 5, 5, 4, 3],
    [3, 4, 5, 5, 4, 3],
    [2, 3, 4, 4, 3, 2],
    [1, 2, 3, 3, 2, 1],
]

def order_moves(board: Board, player: Player, moves: List[Move], tt_best: Optional[Move]) -> List[Move]:
    if tt_best is not None:
        moves = [tt_best] + [m for m in moves if m != tt_best]
        return moves
    def score(m: Move) -> int:
        r, c, q, d = m
        return CENTER_WEIGHTS[r][c]
    return sorted(moves, key=score, reverse=True)

def segment_score(board: Board, player: Player) -> int:
    me = int(player)
    you = int(opponent(player))
    s = 0
    for seg in Board.SEGMENTS:
        mc = 0
        yc = 0
        for r, c in seg:
            v = board.grid[r][c]
            if v == me:
                mc += 1
            elif v == you:
                yc += 1
        if yc == 0 and mc > 0:
            s += 10 ** mc
        elif mc == 0 and yc > 0:
            s -= 10 ** yc
    return s

def evaluate(board: Board, player_to_maximize: Player) -> int:
    STATS["evals"] += 1
    me = player_to_maximize
    you = opponent(me)
    if board.check_five(me):
        return 1_000_000_000
    if board.check_five(you):
        return -1_000_000_000
    return segment_score(board, me)

# --- petit utilitaire de report temps → callback
def _maybe_report(progress_cb: Optional[Callable[[int], None]],
                  start_ts: float,
                  nodes0: int,
                  last_report: List[int],
                  report_every_nodes: int) -> None:
    if progress_cb is None:
        return
    processed = STATS["nodes"] - nodes0
    if processed - last_report[0] >= report_every_nodes:
        last_report[0] = processed
        try:
            progress_cb(int((time.time() - start_ts) * 1000))
        except Exception:
            pass

def search(board: Board,
           player_to_move: Player,
           player_to_maximize: Player,
           depth: int,
           alpha: int,
           beta: int,
           deadline: Optional[float],
           *,
           progress_cb: Optional[Callable[[int], None]],
           start_ts: float,
           nodes0: int,
           last_report: List[int],
           report_every_nodes: int) -> int:
    STATS["nodes"] += 1
    if deadline is not None and time.time() > deadline:
        return evaluate(board, player_to_maximize)
    if depth == 0:
        return evaluate(board, player_to_maximize)

    _maybe_report(progress_cb, start_ts, nodes0, last_report, report_every_nodes)

    key = board_key(board, player_to_move)
    STATS["tt_probe"] += 1
    if key in TT:
        tt_depth, tt_val, tt_flag, tt_move = TT[key]
        if tt_depth >= depth:
            STATS["tt_hit"] += 1
            if tt_flag == 0:
                return tt_val
            if tt_flag < 0 and tt_val <= alpha:
                return tt_val
            if tt_flag > 0 and tt_val >= beta:
                return tt_val
        moves = order_moves(board, player_to_move, generate_moves(board), tt_move)
    else:
        moves = order_moves(board, player_to_move, generate_moves(board), None)

    if player_to_move == player_to_maximize:
        best = -math.inf
        best_mv: Optional[Move] = None
        a0 = alpha
        for mv in moves:
            b2, winner, terminal = apply_move(board, player_to_move, mv)
            if terminal:
                if winner is None:
                    val = 0
                elif winner == player_to_maximize:
                    val = 1_000_000_000 - (10_000 - depth)
                else:
                    val = -1_000_000_000 + (10_000 - depth)
            else:
                val = search(b2, opponent(player_to_move), player_to_maximize, depth - 1, alpha, beta, deadline,
                             progress_cb=progress_cb, start_ts=start_ts, nodes0=nodes0,
                             last_report=last_report, report_every_nodes=report_every_nodes)
            if val > best:
                best = val
                best_mv = mv
            if best > alpha:
                alpha = best
            if beta <= alpha:
                STATS["cuts"] += 1
                break
            _maybe_report(progress_cb, start_ts, nodes0, last_report, report_every_nodes)
        flag = 0
        if best <= a0:
            flag = -1
        elif best >= beta:
            flag = 1
        TT[key] = (depth, int(best), flag, best_mv)
        return int(best)
    else:
        best = math.inf
        best_mv: Optional[Move] = None
        b0 = beta
        for mv in moves:
            b2, winner, terminal = apply_move(board, player_to_move, mv)
            if terminal:
                if winner is None:
                    val = 0
                elif winner == player_to_maximize:
                    val = 1_000_000_000 - (10_000 - depth)
                else:
                    val = -1_000_000_000 + (10_000 - depth)
            else:
                val = search(b2, opponent(player_to_move), player_to_maximize, depth - 1, alpha, beta, deadline,
                             progress_cb=progress_cb, start_ts=start_ts, nodes0=nodes0,
                             last_report=last_report, report_every_nodes=report_every_nodes)
            if val < best:
                best = val
                best_mv = mv
            if best < beta:
                beta = best
            if beta <= alpha:
                STATS["cuts"] += 1
                break
            _maybe_report(progress_cb, start_ts, nodes0, last_report, report_every_nodes)
        flag = 0
        if best <= alpha:
            flag = -1
        elif best >= b0:
            flag = 1
        TT[key] = (depth, int(best), flag, best_mv)
        return int(best)

def best_move(board: Board,
              player_to_move: Player,
              max_depth: int = 3,
              time_ms: Optional[int] = None,
              progress_cb: Optional[Callable[[int], None]] = None) -> Move:
    start_ts = time.time()
    deadline = None if time_ms is None else start_ts + time_ms / 1000.0
    best_mv: Optional[Move] = None
    best_val = -math.inf

    # report ~chaque 2000 nœuds (ajuste si tu veux)
    report_every_nodes = 2000
    nodes0 = STATS["nodes"]
    last_report = [0]

    # premier “heartbeat” pour afficher la barre tout de suite
    _maybe_report(progress_cb, start_ts, nodes0, last_report, report_every_nodes)

    for d in range(1, max_depth + 1):
        if deadline is not None and time.time() > deadline:
            break
        key = board_key(board, player_to_move)
        tt_best = TT[key][3] if key in TT and TT[key][0] >= d - 1 else None
        moves = order_moves(board, player_to_move, generate_moves(board), tt_best)
        cur_best_mv = best_mv
        cur_best_val = best_val
        alpha, beta = -math.inf, math.inf
        for mv in moves:
            if deadline is not None and time.time() > deadline:
                break
            b2, winner, terminal = apply_move(board, player_to_move, mv)
            if terminal:
                if winner is None:
                    val = 0
                elif winner == player_to_move:
                    val = 1_000_000_000 - (10_000 - d)
                else:
                    val = -1_000_000_000 + (10_000 - d)
            else:
                val = search(b2, opponent(player_to_move), player_to_move, d - 1, alpha, beta, deadline,
                             progress_cb=progress_cb, start_ts=start_ts, nodes0=nodes0,
                             last_report=last_report, report_every_nodes=report_every_nodes)
            if val > cur_best_val or cur_best_mv is None:
                cur_best_val = val
                cur_best_mv = mv
            if cur_best_val > alpha:
                alpha = cur_best_val

            _maybe_report(progress_cb, start_ts, nodes0, last_report, report_every_nodes)

        if cur_best_mv is not None:
            best_mv = cur_best_mv
            best_val = cur_best_val
        else:
            break

        _maybe_report(progress_cb, start_ts, nodes0, last_report, report_every_nodes)

    # report final
    if progress_cb is not None:
        try:
            progress_cb(int((time.time() - start_ts) * 1000))
        except Exception:
            pass

    if best_mv is None:
        ms = generate_moves(board)
        return ms[0]
    return best_mv