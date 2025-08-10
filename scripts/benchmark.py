import argparse
import random
import time
from statistics import mean
from pentago.game import Game
from pentago.board import Player
from pentago.ai.minimax import best_move, reset_stats, stats_snapshot

def random_position(plies: int, seed: int = 42):
    random.seed(seed)
    g = Game()
    for _ in range(plies):
        if g.terminal():
            break
        mvs = g.legal_moves()
        mv = random.choice(mvs)
        r, c, q, d = mv
        g.play(r, c, q, d)
    return g

def bench_position(g: Game, side: Player, depth: int, time_ms: int | None, repeats: int):
    times = []
    nodes = []
    evals = []
    cuts = []
    tt_probe = []
    tt_hit = []
    for i in range(repeats):
        reset_stats()
        t0 = time.time()
        _ = best_move(g.board, side, max_depth=depth, time_ms=time_ms)
        dt = time.time() - t0
        s = stats_snapshot()
        times.append(dt)
        nodes.append(s["nodes"])
        evals.append(s["evals"])
        cuts.append(s["cuts"])
        tt_probe.append(s["tt_probe"])
        tt_hit.append(s["tt_hit"])
    return {
        "time_s_avg": mean(times),
        "nodes_avg": int(mean(nodes)),
        "nps": int(mean(nodes) / mean(times)) if mean(times) > 0 else 0,
        "evals_avg": int(mean(evals)),
        "cuts_avg": int(mean(cuts)),
        "tt_probe_avg": int(mean(tt_probe)),
        "tt_hit_avg": int(mean(tt_hit)),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plies", type=int, nargs="+", default=[0, 6, 12, 18])
    parser.add_argument("--depths", type=int, nargs="+", default=[1, 2, 3, 4])
    parser.add_argument("--time", type=int, nargs="*", default=[])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print("Pentago minimax benchmark")
    for p in args.plies:
        g = random_position(p, seed=args.seed)
        side = g.current_player()
        print(f"\nPosition after {p} plies (to move: {'B' if side==Player.BLACK else 'W'})")
        for d in args.depths:
            res = bench_position(g, side, depth=d, time_ms=None, repeats=args.repeats)
            print(f"depth={d:>2}  time={res['time_s_avg']:.3f}s  nodes={res['nodes_avg']:>8}  nps={res['nps']:>8}  evals={res['evals_avg']:>8}  cuts={res['cuts_avg']:>8}  tt_hit={res['tt_hit_avg']:>8}/{res['tt_probe_avg']:>8}")
        for t in args.time:
            res = bench_position(g, side, depth=32, time_ms=t, repeats=args.repeats)
            print(f"time={t:>4}ms depth<=ID  time={res['time_s_avg']:.3f}s  nodes={res['nodes_avg']:>8}  nps={res['nps']:>8}  evals={res['evals_avg']:>8}  cuts={res['cuts_avg']:>8}  tt_hit={res['tt_hit_avg']:>8}/{res['tt_probe_avg']:>8}")

if __name__ == "__main__":
    main()