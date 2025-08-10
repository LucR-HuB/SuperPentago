from pentago.board import Board, Player, Quadrant, Direction

def test_rotate_cw_then_ccw_restores():
    b = Board()
    for r in range(3):
        for c in range(3):
            if (r + c) % 2 == 0:
                b.place(r, c, Player.BLACK)
    ref = b.copy()
    b.rotate(Quadrant.Q00, Direction.CW)
    b.rotate(Quadrant.Q00, Direction.CCW)
    assert b.grid == ref.grid

def test_rotate_affects_only_chosen_quadrant():
    b = Board()
    for r in range(3, 6):
        for c in range(3, 6):
            b.place(r, c, Player.WHITE)
    ref = [row[:] for row in b.grid]
    b.rotate(Quadrant.Q00, Direction.CW)
    for r in range(3, 6):
        for c in range(3, 6):
            assert b.grid[r][c] == ref[r][c]

def test_rotate_mapping_example():
    b = Board()
    b.place(0, 1, Player.BLACK)
    b.rotate(Quadrant.Q00, Direction.CW)
    assert b.at(1, 2) == Player.BLACK