import time
import math
from typing import Dict, Tuple, List, Optional, Callable
from ..board import Board, Player, Quadrant, Direction
from .minimax import CENTER_WEIGHTS

Move = Tuple[int, int, Quadrant, Direction]
Key = Tuple[int, Tuple[int, ...]]

def opponent(p: Player) -> Player:
    return Player.BLACK if p == Player.WHITE else Player.WHITE

def board_key(board: Board, to_move: Player) -> Key:
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

def apply_move(board: Board, player: Player, mv: Move):
    r, c, q, d = mv
    b2 = board.copy()
    b2.place(r, c, player)
    b2.rotate(q, d)
    cur = b2.check_five(player)
    opp = b2.check_five(opponent(player))
    if cur and opp:
        return b2, player, True, None
    if cur:
        return b2, player, True, None
    if opp:
        return b2, opponent(player), True, None
    if b2.full():
        return b2, None, True, None
    return b2, None, False, None

class Node:
    __slots__ = ("N", "P", "Nsa", "Wsa", "children")
    def __init__(self, priors: Dict[Move, float]):
        self.N = 0
        self.P = priors
        self.Nsa: Dict[Move, int] = {}
        self.Wsa: Dict[Move, float] = {}
        self.children: Dict[Move, Key] = {}

TREE: Dict[Key, Node] = {}

def net_policy_value(board: Board, to_move: Player) -> Tuple[Dict[Move, float], float]:
    moves = generate_moves(board)
    if not moves:
        return {}, 0.0
    ws = [CENTER_WEIGHTS[m[0]][m[1]] for m in moves]
    s = float(sum(ws))
    if s <= 0:
        p = 1.0 / len(moves)
        priors = {mv: p for mv in moves}
    else:
        priors = {mv: w / s for mv, w in zip(moves, ws)}
    return priors, 0.0

def best_move(
    board: Board,
    player_to_move: Player,
    time_ms: Optional[int] = None,
    simulations: Optional[int] = None,
    c_puct: float = 1.5,
    progress_cb: Optional[Callable[[int], None]] = None,
) -> Move:
    root_key = board_key(board, player_to_move)
    if root_key not in TREE:
        priors, _ = net_policy_value(board, player_to_move)
        TREE[root_key] = Node(priors)

    deadline = None if time_ms is None else time.time() + time_ms / 1000.0
    sims_target = simulations if simulations is not None else (10_000 if time_ms is None else 1_000_000_000)
    sims = 0
    report_every = 200
    if simulations is not None and sims_target and sims_target > 0:
        report_every = max(1, sims_target // 100)

    while True:
        if deadline is not None and time.time() > deadline:
            break
        if sims >= sims_target:
            break
        sims += 1
        if progress_cb and (sims % report_every == 0):
            try:
                progress_cb(sims)
            except Exception:
                pass

        path: List[Tuple[Key, Move]] = []
        cur_board = board.copy()
        cur_player = player_to_move
        key = root_key
        terminal = False
        winner: Optional[Player] = None

        while True:
            node = TREE[key]
            if not node.P:
                priors, v_est = net_policy_value(cur_board, cur_player)
                if priors:
                    node.P = priors
                else:
                    terminal = True
                    winner = None
                    break

            best = None
            best_m: Optional[Move] = None
            sqrtN = math.sqrt(node.N + 1)
            for m, p in node.P.items():
                nsa = node.Nsa.get(m, 0)
                q = (node.Wsa.get(m, 0.0) / nsa) if nsa > 0 else 0.0
                u = c_puct * p * (sqrtN / (1 + nsa))
                s = q + u
                if best is None or s > best:
                    best = s
                    best_m = m

            mv = best_m
            if mv is None:
                terminal = True
                winner = None
                break

            path.append((key, mv))
            b2, winner, terminal, _ = apply_move(cur_board, cur_player, mv)
            if terminal:
                cur_board = b2
                break

            next_player = opponent(cur_player)
            child_key = board_key(b2, next_player)
            if child_key not in TREE:
                priors, _ = net_policy_value(b2, next_player)
                node.children[mv] = child_key
                TREE[child_key] = Node(priors)
                cur_board = b2
                cur_player = next_player
                key = child_key
                break

            cur_board = b2
            cur_player = next_player
            key = child_key

        if terminal:
            if winner is None:
                v = 0.0
            elif winner == cur_player:
                v = 1.0
            else:
                v = -1.0
        else:
            _, v = net_policy_value(cur_board, cur_player)

        for nk, m in reversed(path):
            n = TREE[nk]
            n.N += 1
            n.Nsa[m] = n.Nsa.get(m, 0) + 1
            n.Wsa[m] = n.Wsa.get(m, 0.0) + v
            v = -v

    if progress_cb:
        try:
            progress_cb(sims)
        except Exception:
            pass

    root = TREE[root_key]
    if not root.P:
        moves = generate_moves(board)
        return moves[0]
    best_mv = None
    best_n = -1
    for m in root.P.keys():
        nsa = root.Nsa.get(m, 0)
        if nsa > best_n:
            best_n = nsa
            best_mv = m
    if best_mv is None:
        moves = generate_moves(board)
        best_mv = moves[0]
    return best_mv  # type: ignore