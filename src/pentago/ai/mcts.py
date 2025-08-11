import time
import random
import math
from typing import Dict, Tuple, List, Optional
from ..board import Board, Player, Quadrant, Direction

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

def uct_score(parent_N: int, child_W: float, child_N: int, c: float) -> float:
    if child_N == 0:
        return float("inf")
    return (child_W / child_N) + c * math.sqrt(math.log(parent_N + 1) / child_N)

def rollout(board: Board, to_move: Player, max_steps: int = 256) -> int:
    b = board.copy()
    p = to_move
    for _ in range(max_steps):
        moves = generate_moves(b)
        if not moves:
            return 0
        mv = random.choice(moves)
        b2, winner, terminal, _ = apply_move(b, p, mv)
        if terminal:
            if winner is None:
                return 0
            return 1 if winner == to_move else -1
        b = b2
        p = opponent(p)
    return 0

def best_move_mcts(board: Board, player_to_move: Player, time_ms: Optional[int] = None, simulations: Optional[int] = None, c_explore: float = 1.414) -> Move:
    deadline = None if time_ms is None else time.time() + time_ms / 1000.0
    sims_target = simulations if simulations is not None else (10_000 if time_ms is None else 1_000_000_000)
    root_key = board_key(board, player_to_move)
    if root_key not in TREE:
        TREE[root_key] = Node(generate_moves(board))
    sims = 0
    while True:
        if deadline is not None and time.time() > deadline:
            break
        if sims >= sims_target:
            break
        sims += 1
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
    root = TREE[root_key]
    if not root.children:
        moves = generate_moves(board)
        return moves[0]
    best_mv = None
    best_N = -1
    for m, ck in root.children.items():
        n = TREE[ck]
        if n.N > best_N:
            best_N = n.N
            best_mv = m
    return best_mv  # type: ignore