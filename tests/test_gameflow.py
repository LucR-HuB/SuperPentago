from pentago.game import Game
from pentago.board import Player, Quadrant, Direction


def test_win_checked_only_after_rotation():
    g = Game()
    g.board.place(0, 0, Player.BLACK)
    g.board.place(0, 1, Player.BLACK)
    g.board.place(0, 2, Player.BLACK)
    g.board.place(0, 3, Player.BLACK)
    g.play(0, 4, Quadrant.Q01, Direction.CW)
    assert g.winner() is None
    assert not g.terminal()
    assert g.current_player() == Player.WHITE


def test_simultaneous_alignments_current_player_wins():
    g = Game()
    g.board.place(0, 0, Player.BLACK)
    g.board.place(1, 0, Player.BLACK)
    g.board.place(2, 0, Player.BLACK)
    g.board.place(3, 0, Player.BLACK)
    g.board.place(5, 1, Player.WHITE)
    g.board.place(5, 2, Player.WHITE)
    g.board.place(5, 4, Player.WHITE)
    g.board.place(3, 3, Player.WHITE)
    g.board.place(5, 3, Player.WHITE)
    g.play(4, 0, Quadrant.Q11, Direction.CCW)
    assert g.terminal()
    assert g.winner() == Player.BLACK