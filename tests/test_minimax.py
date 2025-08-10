from pentago.board import Board, Player
from pentago.ai.minimax import best_move

def test_best_move_returns_legal_on_empty_board():
    b = Board()
    mv = best_move(b, Player.BLACK, max_depth=3, time_ms=500)
    r, c, q, d = mv
    assert 0 <= r < 6 and 0 <= c < 6

def test_center_bias_on_empty_board():
    b = Board()
    mv = best_move(b, Player.BLACK, max_depth=1)
    r, c, q, d = mv
    assert r in (2, 3) and c in (2, 3)