import time
import random
import math
from typing import Dict, Tuple, List, Optional, Callable
from ..board import Board, Player, Quadrant, Direction
from .minimax import evaluate as static_eval, CENTER_WEIGHTS  

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
    __slots__ = ("N", "W", "untried", "children")

    def __init__(self, moves: List[Move]):
        self.N = 0
        self.W = 0.0
        self.untried = moves[:]
        self.children: Dict[Move, Key] = {}


TREE: Dict[Key, Node] = {}
ROOT: Optional[Key] = None


def uct_score(parent_N: int, child_W: float, child_N: int, c: float) -> float:
    if child_N == 0:
        return float("inf")
    return (child_W / child_N) + c * math.sqrt(max(1.0, math.log(parent_N + 1)) / child_N)

def immediate_win_move(board: Board, player: Player, moves: List[Move]) -> Optional[Move]:
    for mv in moves:
        b2, winner, terminal, _ = apply_move(board, player, mv)
        if terminal and winner == player:
            return mv
    return None


def opponent_has_immediate_win(board: Board, opp: Player) -> bool:
    for mv in generate_moves(board):
        b2, winner, terminal, _ = apply_move(board, opp, mv)
        if terminal and winner == opp:
            return True
    return False


def block_opponent_win(board: Board, player: Player, moves: List[Move]) -> Optional[Move]:
    opp = opponent(player)
    if not opponent_has_immediate_win(board, opp):
        return None
    for mv in moves:
        b2, _, terminal, _ = apply_move(board, player, mv)
        if terminal:
            continue
        if not opponent_has_immediate_win(b2, opp):
            return mv
    return None


def move_center_score(mv: Move) -> int:
    r, c, _, _ = mv
    return CENTER_WEIGHTS[r][c]


def heuristic_pick_move(board: Board, player: Player, moves: List[Move]) -> Move:
    return max(moves, key=move_center_score)


def rollout(board: Board, to_move: Player, max_steps: int = 32) -> int:
    b = board.copy()
    p = to_move
    steps = 0
    while True:
        moves = generate_moves(b)
        if not moves:
            return 0  
        mv = immediate_win_move(b, p, moves)
        if mv is not None:
            b2, winner, terminal, _ = apply_move(b, p, mv)
            return 1 if winner == to_move else (-1 if winner is not None else 0)

        mv = block_opponent_win(b, p, moves)
        if mv is None:
            mv = heuristic_pick_move(b, p, moves)

        b2, winner, terminal, _ = apply_move(b, p, mv)
        if terminal:
            if winner is None:
                return 0
            return 1 if winner == to_move else -1

        b = b2
        p = opponent(p)
        steps += 1

        if steps >= max_steps:
            ev = static_eval(b, to_move)
            if ev > 0:
                return 1
            if ev < 0:
                return -1
            return 0
def mcts_reset() -> None:
    global TREE, ROOT
    TREE.clear()
    ROOT = None


def _prune_unreachable(root_key: Key) -> None:
    keep: set[Key] = set()
    stack: List[Key] = [root_key]
    while stack:
        k = stack.pop()
        if k in keep:
            continue
        keep.add(k)
        n = TREE.get(k)
        if n is None:
            continue
        for ck in n.children.values():
            if ck not in keep:
                stack.append(ck)
    for k in list(TREE.keys()):
        if k not in keep:
            del TREE[k]
    for n in TREE.values():
        n.children = {m: ck for m, ck in n.children.items() if ck in TREE}


def mcts_rebase(board: Board, to_move: Player, prune: bool = True) -> None:
    global ROOT
    rk = board_key(board, to_move)
    if rk not in TREE:
        TREE[rk] = Node(generate_moves(board))
    ROOT = rk
    if prune:
        _prune_unreachable(rk)
        
def best_move_mcts(
    board: Board,
    player_to_move: Player,
    time_ms: Optional[int] = None,
    simulations: Optional[int] = None,
    c_explore: float = 1.414,
    progress_cb: Optional[Callable[[int], None]] = None,
) -> Move:
    root_key = board_key(board, player_to_move)
    if root_key not in TREE:
        TREE[root_key] = Node(generate_moves(board))

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
        node = TREE[key]
        terminal = False
        winner = None

        while not node.untried and node.children:
            best = None
            best_m = None
            for m, ck in node.children.items():
                ch = TREE[ck]
                s = uct_score(node.N, ch.W, ch.N, c_explore)
                if best is None or s > best:
                    best = s
                    best_m = m
            mv = best_m
            path.append((key, mv))
            cur_board, winner, terminal, _ = apply_move(cur_board, cur_player, mv)  # type: ignore
            if terminal:
                break
            cur_player = opponent(cur_player)
            key = board_key(cur_board, cur_player)
            if key not in TREE:
                TREE[key] = Node(generate_moves(cur_board))
            node = TREE[key]

        if not terminal:
            if node.untried:
                mv = node.untried.pop(random.randrange(len(node.untried)))
                b2, winner, terminal, _ = apply_move(cur_board, cur_player, mv)
                path.append((key, mv))
                next_player = opponent(cur_player)
                child_key = board_key(b2, next_player if not terminal else cur_player)
                node.children[mv] = child_key
                if child_key not in TREE:
                    TREE[child_key] = Node([] if terminal else generate_moves(b2))
                cur_board = b2
                cur_player = next_player
                key = child_key
                node = TREE[key]

        if terminal:
            if winner is None:
                reward = 0
            elif winner == player_to_move:
                reward = 1
            else:
                reward = -1
        else:
            reward = rollout(cur_board, cur_player)

        for nk, _ in path:
            n = TREE[nk]
            n.N += 1
            n.W += reward

    if progress_cb:
        try:
            progress_cb(sims)
        except Exception:
            pass

    root = TREE[root_key]
    if not root.children:
        moves = generate_moves(board)
        return moves[0]

    best_mv = None
    best_q = -float("inf")
    for m, ck in root.children.items():
        n = TREE[ck]
        if n.N > 0:
            q = n.W / n.N
            if q > best_q:
                best_q = q
                best_mv = m

    if best_mv is None:
        moves = generate_moves(board)
        best_mv = moves[0]
    return best_mv  # type: ignore