import sys
import argparse
from typing import Tuple
from pentago.game import Game
from pentago.board import Quadrant, Direction, Player
from pentago.ai.minimax import best_move

COLS = "ABCDEF"
ROWS = "123456"

def render_board(g: Game) -> None:
    grid = g.board.grid
    sep = "  +---+---+---+---+---+---+"
    print("    " + "   ".join(COLS))
    for r in range(6):
        if r in (0, 3):
            print(sep)
        line = []
        for c in range(6):
            v = grid[r][c]
            ch = "." if v == 0 else ("B" if v == int(Player.BLACK) else "W")
            line.append(ch)
        left = str(r + 1) + " | "
        mid = " | ".join(line[:3]) + " || " + " | ".join(line[3:])
        print(left + mid + " |")
    print(sep)

def parse_move(s: str) -> Tuple[int, int, Quadrant, Direction]:
    parts = s.strip().upper().split()
    if len(parts) != 3:
        raise ValueError("Format")
    cell, quad, direc = parts
    if len(cell) != 2 or cell[0] not in COLS or cell[1] not in ROWS:
        raise ValueError("Cell")
    c = COLS.index(cell[0])
    r = ROWS.index(cell[1])
    qmap = {"Q00": Quadrant.Q00, "Q01": Quadrant.Q01, "Q10": Quadrant.Q10, "Q11": Quadrant.Q11}
    if quad not in qmap:
        raise ValueError("Quadrant")
    q = qmap[quad]
    dmap = {"CW": Direction.CW, "CCW": Direction.CCW}
    if direc not in dmap:
        raise ValueError("Direction")
    d = dmap[direc]
    return r, c, q, d

def move_to_str(r: int, c: int, q: Quadrant, d: Direction) -> str:
    cell = f"{COLS[c]}{ROWS[r]}"
    qname = {Quadrant.Q00: "Q00", Quadrant.Q01: "Q01", Quadrant.Q10: "Q10", Quadrant.Q11: "Q11"}[q]
    dname = "CW" if d == Direction.CW else "CCW"
    return f"{cell} {qname} {dname}"

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bot", choices=["black", "white", "none"], default="none")
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--time", type=int, default=None)
    args = parser.parse_args()

    g = Game()
    print("Pentago CLI")
    print("Enter moves like: E5 Q01 CW")
    print("Commands: help, board, quit")
    render_board(g)

    bot_side = None
    if args.bot == "black":
        bot_side = Player.BLACK
    elif args.bot == "white":
        bot_side = Player.WHITE

    while not g.terminal():
        p = "B" if g.current_player() == Player.BLACK else "W"
        if bot_side is not None and g.current_player() == bot_side:
            mv = best_move(g.board, g.current_player(), max_depth=args.depth, time_ms=args.time)
            r, c, q, d = mv
            print(f"[{p}-BOT] plays: {move_to_str(r, c, q, d)}")
            g.play(r, c, q, d)
            render_board(g)
            continue
        try:
            s = input(f"[{p}] > ").strip()
        except EOFError:
            print()
            break
        if not s:
            continue
        if s.lower() in ("q", "quit", "exit"):
            print("Bye.")
            return 0
        if s.lower() in ("h", "help", "?"):
            print("Move format: <Cell> <Quadrant> <Direction>")
            print("Cell: A-F + 1-6 (e.g., E5)")
            print("Quadrant: Q00 Q01 Q10 Q11")
            print("Direction: CW or CCW")
            print("Args: --bot black|white|none --depth N --time MS")
            continue
        if s.lower() in ("b", "board"):
            render_board(g)
            continue
        try:
            r, c, q, d = parse_move(s)
            g.play(r, c, q, d)
            render_board(g)
        except Exception as e:
            print(f"Invalid move: {e}")
            continue
    if g.winner() is not None:
        w = "Black" if g.winner() == Player.BLACK else "White"
        print(f"Winner: {w}")
    elif g.is_draw():
        print("Draw.")
    return 0

if __name__ == "__main__":
    sys.exit(main())