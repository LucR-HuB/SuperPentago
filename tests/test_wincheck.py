from pentago.board import Board, Player

def test_check_five_horizontal_black():
    b = Board()
    for c in range(5):
        b.place(0, c, Player.BLACK)
    assert b.check_five(Player.BLACK)
    assert not b.check_five(Player.WHITE)

def test_check_five_vertical_white():
    b = Board()
    for r in range(5):
        b.place(r, 4, Player.WHITE)
    assert b.check_five(Player.WHITE)
    assert not b.check_five(Player.BLACK)

def test_check_five_diagonal_black():
    b = Board()
    for k in range(5):
        b.place(k, k, Player.BLACK)
    assert b.check_five(Player.BLACK)

def test_no_false_positive_on_four():
    b = Board()
    for c in range(4):
        b.place(5, c, Player.BLACK)
    assert not b.check_five(Player.BLACK)