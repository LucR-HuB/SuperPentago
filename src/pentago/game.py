from typing import List, Tuple, Optional
from .board import Board, Player, Quadrant, Direction


def _opponent(p: Player) -> Player:
    return Player.BLACK if p == Player.WHITE else Player.WHITE


class Game:
    def __init__(self) -> None:
        self.board = Board()
        self.to_move: Player = Player.BLACK
        self._winner: Optional[Player] = None
        self._draw: bool = False

    def current_player(self) -> Player:
        return self.to_move

    def legal_moves(self) -> List[Tuple[int, int, Quadrant, Direction]]:
        if self.terminal():
            return []
        moves = []
        for r, c in self.board.legal_placements():
            for q in (Quadrant.Q00, Quadrant.Q01, Quadrant.Q10, Quadrant.Q11):
                for d in (Direction.CW, Direction.CCW):
                    moves.append((r, c, q, d))
        return moves

    def play(self, r: int, c: int, q: Quadrant, d: Direction) -> None:
        if self.terminal():
            raise RuntimeError("Game over")
        self.board.place(r, c, self.to_move)
        self.board.rotate(q, d)
        cur = self.board.check_five(self.to_move)
        opp = self.board.check_five(_opponent(self.to_move))
        if cur and opp:
            self._winner = self.to_move
        elif cur:
            self._winner = self.to_move
        elif opp:
            self._winner = _opponent(self.to_move)
        elif self.board.full():
            self._draw = True
        else:
            self.to_move = _opponent(self.to_move)

    def terminal(self) -> bool:
        return self._winner is not None or self._draw

    def winner(self) -> Optional[Player]:
        return self._winner

    def is_draw(self) -> bool:
        return self._draw