from enum import IntEnum
from typing import List, Tuple


class Player(IntEnum):
    BLACK = 1
    WHITE = 2


class Quadrant(IntEnum):
    Q00 = 0
    Q01 = 1
    Q10 = 2
    Q11 = 3


class Direction(IntEnum):
    CW = 1
    CCW = -1


def _compute_segments() -> List[List[Tuple[int, int]]]:
    segments = []
    for r in range(6):
        for c in range(6 - 4):
            segments.append([(r, c + k) for k in range(5)])
    for c in range(6):
        for r in range(6 - 4):
            segments.append([(r + k, c) for k in range(5)])
    for r in range(6):
        for c in range(6):
            if r + 4 < 6 and c + 4 < 6:
                segments.append([(r + k, c + k) for k in range(5)])
            if r + 4 < 6 and c - 4 >= 0:
                segments.append([(r + k, c - k) for k in range(5)])
    uniq = []
    seen = set()
    for seg in segments:
        key = tuple(seg)
        if key not in seen:
            seen.add(key)
            uniq.append(seg)
    return uniq


class Board:
    SEGMENTS = _compute_segments()

    def __init__(self) -> None:
        self.grid: List[List[int]] = [[0 for _ in range(6)] for _ in range(6)]

    def copy(self) -> "Board":
        b = Board()
        b.grid = [row[:] for row in self.grid]
        return b

    def at(self, r: int, c: int) -> int:
        return self.grid[r][c]

    def place(self, r: int, c: int, player: Player) -> None:
        if self.grid[r][c] != 0:
            raise ValueError("Cell not empty")
        self.grid[r][c] = int(player)

    def rotate(self, q: Quadrant, d: Direction) -> None:
        if q == Quadrant.Q00:
            r0, c0 = 0, 0
        elif q == Quadrant.Q01:
            r0, c0 = 0, 3
        elif q == Quadrant.Q10:
            r0, c0 = 3, 0
        else:
            r0, c0 = 3, 3
        sub = [[self.grid[r0 + i][c0 + j] for j in range(3)] for i in range(3)]
        rot = [[0] * 3 for _ in range(3)]
        if d == Direction.CW:
            for i in range(3):
                for j in range(3):
                    rot[j][2 - i] = sub[i][j]
        elif d == Direction.CCW:
            for i in range(3):
                for j in range(3):
                    rot[2 - j][i] = sub[i][j]
        else:
            raise ValueError("Invalid direction")
        for i in range(3):
            for j in range(3):
                self.grid[r0 + i][c0 + j] = rot[i][j]

    def legal_placements(self) -> List[Tuple[int, int]]:
        out = []
        for r in range(6):
            for c in range(6):
                if self.grid[r][c] == 0:
                    out.append((r, c))
        return out

    def check_five(self, player: Player) -> bool:
        p = int(player)
        for seg in Board.SEGMENTS:
            ok = True
            for r, c in seg:
                if self.grid[r][c] != p:
                    ok = False
                    break
            if ok:
                return True
        return False

    def full(self) -> bool:
        for r in range(6):
            for c in range(6):
                if self.grid[r][c] == 0:
                    return False
        return True