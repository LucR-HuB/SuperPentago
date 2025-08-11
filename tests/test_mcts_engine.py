import random
from pentago.game import Game
from pentago.board import Player
from pentago.ai.mcts import best_move_mcts

def stones(g: Game) -> int:
    return sum(1 for r in range(6) for c in range(6) if g.board.grid[r][c] != 0)

def test_best_move_mcts_returns_legal_move():
    random.seed(0)
    g = Game()
    s0 = stones(g)
    r, c, q, d = best_move_mcts(g.board, player_to_move=g.current_player(), simulations=30)
    assert g.board.grid[r][c] == 0
    g.play(r, c, q, d)
    assert stones(g) == s0 + 1
    if not g.terminal():
        assert g.current_player() == Player.WHITE

def test_mcts_two_moves_progresses():
    random.seed(1)
    g = Game()
    s0 = stones(g)
    r1, c1, q1, d1 = best_move_mcts(g.board, player_to_move=g.current_player(), simulations=25)
    assert g.board.grid[r1][c1] == 0
    g.play(r1, c1, q1, d1)
    assert stones(g) == s0 + 1
    if not g.terminal():
        s1 = stones(g)
        r2, c2, q2, d2 = best_move_mcts(g.board, player_to_move=g.current_player(), simulations=25)
        assert g.board.grid[r2][c2] == 0
        g.play(r2, c2, q2, d2)
        assert stones(g) == s1 + 1