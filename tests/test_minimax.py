from pentago.board import Board, Player, Quadrant, Direction
from pentago.game import Game
from pentago.ai.minimax import best_move

def test_minimax_takes_immediate_win():
    b = Board()
    b.place(0, 0, Player.BLACK)
    b.place(0, 1, Player.BLACK)
    b.place(0, 2, Player.BLACK)
    b.place(0, 3, Player.BLACK)
    mv = best_move(b, Player.BLACK, max_depth=1)
    r, c, q, d = mv
    assert r == 0 and c == 4
    g = Game()
    g.board = b.copy()
    g.to_move = Player.BLACK
    g.play(r, c, q, d)
    assert g.winner() == Player.BLACK

def test_minimax_blocks_opponent_threat_depth2():
    b = Board()
    b.place(0, 0, Player.WHITE)
    b.place(0, 1, Player.WHITE)
    b.place(0, 2, Player.WHITE)
    b.place(0, 3, Player.WHITE)
    mv = best_move(b, Player.BLACK, max_depth=2)
    r, c, q, d = mv
    assert r == 0 and c == 4