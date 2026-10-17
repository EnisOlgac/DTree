"""Performance benchmarks for DTree.

Usage (from the python/ folder):

    python benchmarks/bench.py                 # sizes 10,000 and 100,000
    python benchmarks/bench.py 1000 1000000    # custom sizes
    python benchmarks/bench.py --quick         # small sizes, a few seconds
    python benchmarks/bench.py --dynamic       # only insertions and queries alternating

For each tree shape it reports the build time and how often positions in Q1
and Q2 had to be renumbered, then times the queries and structural changes.
Finally it compares reachability with the parent walk of classical doubly linked
trees, for single pairs and for and/or queries (VMin, VMax, UMin, UMax), over increasing depth,
and under dynamic updates, with insertions and queries alternating (including static
pre/post numbers recomputed after each insertion).
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
    # a chain of 3,000, then new leaves under the spine nodes from the top down, repeatedly:
    # finding the end of a subtree by walking down the last children would be O(depth) here
    "top-down comb": lambda i, names, rnd: names[-1] if i < 3000 else f"n{(i - 3000) % 3000}",
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
    timed("can_reach (names)", queries, lambda: sum(t.can_reach(u, v) for u, v in pairs))
    handles = [(t.get_node(u), t.get_node(v)) for u, v in pairs]
    timed("can_reach (handles)", queries, lambda: sum(t.can_reach(u, v) for u, v in handles))
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


def build_with_depth(n, depth, seed=1):
    """A spine (chain) of `depth` nodes; all other nodes hang at random under spine nodes."""
    rnd = random.Random(seed)
    t, names = DTree("D"), ["n0"]
    for i in range(1, n):
        if i < depth:
            parent = names[-1]                       # extend the spine
        else:
            parent = names[rnd.randrange(min(depth, len(names)))]
        t.insert(parent, f"n{i}")
        names.append(f"n{i}")
    return t, names


def parent_walk(parent, u, v):
    """What classical doubly linked trees do: climb from v towards the root, looking for u."""
    w = parent.get(v)
    while w is not None:
        if w == u:
            return True
        w = parent.get(w)
    return False


def ancestors_in(parent, v, members):
    """Climb once from v towards the root and count the ancestors of v that lie in members."""
    hits, w = 0, parent.get(v)
    while w is not None:
        if w in members:
            hits += 1
        w = parent.get(w)
    return hits


def bench_depth(n, depths, queries):
    print(f"\n### Reachability by depth: DTree vs parent walk ({n:,} nodes, {queries:,} random pairs)\n")
    row("depth", "DTree [µs]", "parent walk [µs]", "factor")
    row("---:", "---:", "---:", "---:")
    for depth in depths:
        t, names = build_with_depth(n, depth)
        parent = t._parent
        rnd = random.Random(2)
        pairs = [(rnd.choice(names), rnd.choice(names)) for _ in range(queries)]
        start = time.perf_counter()
        a = [t.can_reach(u, v) for u, v in pairs]
        d = time.perf_counter() - start
        start = time.perf_counter()
        b = [parent_walk(parent, u, v) for u, v in pairs]
        w = time.perf_counter() - start
        assert a == b
        row(f"{depth:,}", f"{d / queries * 1e6:.2f}", f"{w / queries * 1e6:.2f}", factor(w, d))


def bench_sets(n, depths, k, queries):
    print(f"\n### And/or queries: constructed nodes vs parent walk ({n:,} nodes, set of {k:,} nodes, {queries:,} query nodes)\n")
    row("depth", "question", "DTree [µs]", "parent walk [µs]", "factor")
    row("---:", "---", "---:", "---:", "---:")
    for depth in depths:
        t, names = build_with_depth(n, depth)
        parent = t._parent
        rnd = random.Random(4)
        S = rnd.sample(names, k)
        U = [rnd.choice(names) for _ in range(queries)]
        start = time.perf_counter()
        vmin, vmax, umin, umax = t.vmin(S), t.vmax(S), t.umin(S), t.umax(S)
        build = time.perf_counter() - start
        members = set(S)
        # "reaches": climb from every member looking for u. "reached by": climb once from u,
        # looking each ancestor up in a hash set of the members (the best a parent walk can do).
        for name, v_q, walk_q in (
            ("reaches all", vmin.reaches_all, lambda u: all(parent_walk(parent, u, v) for v in S)),
            ("reaches some", vmax.reaches_some, lambda u: any(parent_walk(parent, u, v) for v in S)),
            ("reached by all", umax.reached_by_all, lambda u: ancestors_in(parent, u, members) == len(members)),
            ("reached by some", umin.reached_by_some, lambda u: ancestors_in(parent, u, members) > 0),
        ):
            start = time.perf_counter()
            a = [v_q(u) for u in U]
            d = time.perf_counter() - start
            start = time.perf_counter()
            b = [walk_q(u) for u in U]
            w = time.perf_counter() - start
            assert a == b, name
            row(f"{depth:,}", name, f"{d / queries * 1e6:.2f}", f"{w / queries * 1e6:.1f}", factor(w, d))
    print(f"\n(Building VMin, VMax, UMin and UMax for {k:,} nodes: {build * 1e3:.1f} ms, once per set.)")


def factor(slow, fast):
    return f"{slow / fast:.1f}×" if slow < 10 * fast else f"{slow / fast:,.0f}×"


def dynamic_workload(n, depth, queries_per_insert, seed=5):
    """The same sequence for every contender: insertions (a spine of `depth` nodes, the
    others attached at random to spine nodes) with random queries among the nodes present."""
    rnd = random.Random(seed)
    steps = []
    for i in range(1, n):
        parent = i - 1 if i < depth else rnd.randrange(min(depth, i))
        qs = [(rnd.randrange(i + 1), rnd.randrange(i + 1)) for _ in range(queries_per_insert)]
        steps.append((parent, i, qs))
    return steps


def run_dtree(steps):
    """DTree with node handles (insert returns the new node's handle)."""
    t, answers = DTree("D"), []
    nodes = [None] * (len(steps) + 1)
    for p, c, qs in steps:
        if c == 1:
            nodes[1] = t.insert("n0", "n1")
            nodes[0] = t.get_node("n0")
        else:
            nodes[c] = t.insert(nodes[p], f"n{c}")
        for u, v in qs:
            answers.append(t.can_reach(nodes[u], nodes[v]))
    return answers


def run_parent_walk(steps):
    parent, answers = {}, []
    for p, c, qs in steps:
        parent[c] = p
        for u, v in qs:
            answers.append(parent_walk(parent, u, v))
    return answers


def run_static_numbers(steps):
    """Pre- and post-order numbers from a traversal, recomputed before a query whenever the
    tree has changed: O(1) queries, but every insertion invalidates all numbers."""
    children, answers = {}, []
    pre = post = None
    for p, c, qs in steps:
        children.setdefault(p, []).append(c)
        pre = None                                     # the insertion invalidates the numbers
        for u, v in qs:
            if pre is None:
                pre, post, clock = {}, {}, 0
                stack = [(0, False)]
                while stack:
                    x, done = stack.pop()
                    if done:
                        post[x] = clock
                        clock += 1
                        continue
                    pre[x] = clock
                    clock += 1
                    stack.append((x, True))
                    stack.extend((k, False) for k in reversed(children.get(x, ())))
            answers.append(pre[u] < pre[v] and post[v] < post[u])
    return answers


def timed(run, steps):
    start = time.perf_counter()
    answers = run(steps)
    return time.perf_counter() - start, answers


def bench_dynamic(n, depths, static_sizes, queries_per_insert=1):
    print(f"\n### Dynamic updates: insertions and queries alternating "
          f"({n:,} nodes, {queries_per_insert} random query per insertion)\n")
    row("depth", "DTree [µs per step]", "parent walk [µs per step]", "factor")
    row("---:", "---:", "---:", "---:")
    for depth in depths:
        steps = dynamic_workload(n, depth, queries_per_insert)
        d, a = timed(run_dtree, steps)
        w, b = timed(run_parent_walk, steps)
        assert a == b
        row(f"{depth:,}", f"{d / len(steps) * 1e6:.2f}", f"{w / len(steps) * 1e6:.2f}", factor(w, d))
    print(f"\n### Dynamic updates with static pre/post numbers, recomputed after each insertion "
          f"(depth 100, {queries_per_insert} query per insertion)\n")
    row("nodes", "DTree [ms]", "parent walk [ms]", "static numbers [ms]")
    row("---:", "---:", "---:", "---:")
    for m in static_sizes:
        steps = dynamic_workload(m, 100, queries_per_insert)
        d, a = timed(run_dtree, steps)
        w, b = timed(run_parent_walk, steps)
        r, c = timed(run_static_numbers, steps)
        assert a == b == c
        row(f"{m:,}", f"{d * 1e3:,.1f}", f"{w * 1e3:,.1f}", f"{r * 1e3:,.0f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sizes", nargs="*", type=int, help="tree sizes (default: 10000 100000)")
    ap.add_argument("--quick", action="store_true", help="small sizes for a fast check")
    ap.add_argument("--dynamic", action="store_true", help="only the dynamic updates")
    args = ap.parse_args()
    if args.dynamic:
        print(f"DTree benchmarks, Python {sys.version.split()[0]}")
        if args.quick:
            bench_dynamic(5_000, [10, 100, 1_000], [500, 1_000, 2_000])
        else:
            bench_dynamic(20_000, [10, 100, 1_000, 10_000], [1_000, 2_000, 5_000])
        return
    sizes = [1_000, 10_000] if args.quick else (args.sizes or [10_000, 100_000])
    print(f"DTree benchmarks, Python {sys.version.split()[0]}")
    bench_build(sizes)
    bench_lists(sizes)
    bench_operations(max(sizes), queries=100_000 if args.quick else 1_000_000)
    if args.quick:
        bench_depth(10_000, [10, 100, 1_000, 10_000], 20_000)
        bench_sets(10_000, [10, 100, 1_000], 100, 200)
        bench_dynamic(5_000, [10, 100, 1_000], [500, 1_000, 2_000])
    else:
        bench_depth(100_000, [10, 100, 1_000, 10_000, 100_000], 20_000)
        bench_sets(100_000, [10, 100, 1_000, 10_000], 1_000, 200)
        bench_dynamic(20_000, [10, 100, 1_000, 10_000], [1_000, 2_000, 5_000])


if __name__ == "__main__":
    main()
