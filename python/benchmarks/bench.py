"""Performance benchmarks for DTree.

Usage (from the python/ folder):

    python benchmarks/bench.py                 # sizes 10,000 and 100,000
    python benchmarks/bench.py 1000 1000000    # custom sizes
    python benchmarks/bench.py --quick         # small sizes, a few seconds

For each tree shape it reports the build time and how often positions in Q1
and Q2 had to be renumbered, then times the queries and structural changes.
Timings depend on the machine; the renumbering counts do not.
"""

import argparse
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dtree import SINK, SOURCE, DList, DTree  # noqa: E402

SHAPES = {
    # name: function(i, names, rnd) -> parent of the new node n{i}
    "random": lambda i, names, rnd: rnd.choice(names),
    "chain": lambda i, names, rnd: names[-1],
    "star (root)": lambda i, names, rnd: "n0",
    "star (inner node)": lambda i, names, rnd: "n1",
    # worst case for rational positions: always the newer half-gap, alternating sides
    "alternating": lambda i, names, rnd: f"n{2 * ((i - 1) // 2)}",
}


def build(shape, n, seed=1):
    rnd = random.Random(seed)
    t, names = DTree("B"), ["n0"]
    pick = SHAPES[shape]
    start = time.perf_counter()
    for i in range(1, n):
        if shape == "star (inner node)" and i <= 2:
            parent = "n0"  # n1 and n2 under the root, so n1 has a right neighbor
        else:
            parent = pick(i, names, rnd)
        t.insert(parent, f"n{i}")
        names.append(f"n{i}")
    return t, names, time.perf_counter() - start


def stats(q):
    return q.renumber_count, q.renumber_moved


def row(*cells):
    print("| " + " | ".join(str(c) for c in cells) + " |")


def bench_build(sizes):
    print("\n### Building trees\n")
    row("shape", "nodes", "time [s]", "renumberings Q1 / Q2", "positions moved per insertion")
    row("---", "---:", "---:", "---:", "---:")
    for shape in SHAPES:
        for n in sizes:
            t, _, dt = build(shape, n)
            c1, m1 = stats(t.Q1)
            c2, m2 = stats(t.Q2)
            row(shape, f"{n:,}", f"{dt:.2f}", f"{c1:,} / {c2:,}", f"{(m1 + m2) / (2 * n):.2f}")


def bench_lists(sizes):
    print("\n### Growing a single list (DList)\n")
    row("pattern", "nodes", "time [s]", "renumberings")
    row("---", "---:", "---:", "---:")
    for pattern in ("append", "prepend", "alternate"):
        for n in sizes:
            q = DList("Q")
            start = time.perf_counter()
            for i in range(n):
                right = pattern == "append" or (pattern == "alternate" and i % 2)
                if right:
                    q.insert_before(f"v{i}", SINK)
                else:
                    q.insert_after(f"v{i}", SOURCE)
            row(pattern, f"{n:,}", f"{time.perf_counter() - start:.2f}", f"{q.renumber_count:,}")


def bench_operations(n, queries=1_000_000):
    print(f"\n### Queries and changes on a random tree of {n:,} nodes\n")
    row("operation", "count", "time [s]", "per operation [µs]")
    row("---", "---:", "---:", "---:")
    rnd = random.Random(2)

    def timed(name, count, fn):
        start = time.perf_counter()
        fn()
        dt = time.perf_counter() - start
        row(name, f"{count:,}", f"{dt:.2f}", f"{dt / count * 1e6:.1f}")

    t, names, _ = build("random", n)
    pairs = [(rnd.choice(names), rnd.choice(names)) for _ in range(queries)]
    timed("can_reach", queries, lambda: sum(t.can_reach(u, v) for u, v in pairs))
    timed("depth", len(names), lambda: sum(t.depth(v) for v in names))

    k = max(1, n // 10)
    t, names, _ = build("random", n)
    victims = rnd.sample(names[1:], k)
    timed("delete", k, lambda: [t.delete(v) for v in victims])

    t, names, _ = build("random", n)
    moves = []
    while len(moves) < max(1, n // 100):
        u, p = rnd.choice(names[1:]), rnd.choice(names)
        moves.append((u, p))

    def do_moves():
        for u, p in moves:
            if t.contains(u) and t.contains(p) and u != p and not t.can_reach(u, p):
                t.cut_n_paste(u, p)

    timed("cut_n_paste", len(moves), do_moves)

    t, names, _ = build("random", n)
    leaves = [v for v in names if t.is_leaf(v)][: max(1, n // 10)]
    parents = list({t.get_parent(v) for v in leaves if t.get_parent(v)})
    timed("delete_subtree", len(parents), lambda: [t.delete_subtree(v) for v in parents if t.contains(v) and not t.is_root(v)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sizes", nargs="*", type=int, help="tree sizes (default: 10000 100000)")
    ap.add_argument("--quick", action="store_true", help="small sizes for a fast check")
    args = ap.parse_args()
    sizes = [1_000, 10_000] if args.quick else (args.sizes or [10_000, 100_000])
    print(f"DTree benchmarks, Python {sys.version.split()[0]}")
    bench_build(sizes)
    bench_lists(sizes)
    bench_operations(max(sizes), queries=100_000 if args.quick else 1_000_000)


if __name__ == "__main__":
    main()
