# DTree for Python

Python implementation of the `DTree` API (see [`../docs/API.md`](../docs/API.md)). No dependencies; Python 3.8+.

```python
from dtree import DTree

t = DTree("P1")
t.insert("A", "B")
t.insert("B", "C")

t.can_reach("A", "C")    # True
t.path_to_root("C")      # ['C', 'B', 'A']
t.q1, t.q2               # (['A', 'B', 'C'], ['A', 'B', 'C'])

t.insert("A", "D")
t.cut_n_paste("C", "D")  # move subtree C under D
t.delete("B")            # B's children (none left) move up to A
t.delete_subtree("D")    # removes D and C
```

Load one of the example files (`parent: child1; child2` per line):

```python
t = DTree.from_file("../examples/Test.csx")
```

## API (C# name → Python name)

| C# (docs) | Python |
|---|---|
| `DTree(id)` | `DTree(tree_id="P1")` |
| `Insert(parent, child)` | `insert(parent, child)` |
| `Contains(node)` | `contains(node)` / `node in t` |
| `GetParent(node)` | `get_parent(node)` (`None` for the root) |
| `CutNPaste(u, p)` | `cut_n_paste(subtree_root, new_parent)` |
| `Delete(node)` | `delete(node)`—children move up to the parent |
| — | `delete_subtree(node)`—removes the node and all descendants |
| `Q1`, `Q2` | `Q1`, `Q2` (the `DList` projections, for list-level checks); `q1`, `q2` (plain lists, without the `[` `]` markers) |
| `Source`, `Sink` | `source`, `sink` |
| `CanReach`, `CanNotReach` | `can_reach`, `can_not_reach` |
| `IsRoot`, `IsLeaf` | `is_root`, `is_leaf` |
| `IsAncestor`, `IsDescendant` | `is_ancestor`, `is_descendant` |
| `SameSubtree`, `SubtreeSize` | `same_subtree`, `subtree_size` (plus `subtree`) |
| `Depth` | `depth` (root = 0) |
| `PathToRoot`, `RootToPath` | `path_to_root`, `root_to_path` (plus `path(u, v)`) |

## Semantics

- `can_reach(u, v)` is irreflexive: no node reaches itself, so `can_reach(u, u)` is `False`. (The C# prototype is reflexive.)
- `is_ancestor(u, v)` equals `can_reach(u, v)` and is likewise proper.
- `delete(v)` re-attaches v's children to v's parent, in v's place among its siblings.
- `delete_subtree(v)` removes v with all its descendants and returns them in Q1 order.
- `cut_n_paste(u, p)` moves the subtree rooted at u under p as p's last child; p must not lie inside u's subtree.
- Projection positions are fractions: a new node gets the mediant (a+c)/(b+d) of its neighbors, so normally no other node moves. Only rare alternating insertion patterns trigger a local renumbering. Tree depth and width are unbounded. `t.Q1.index(v)` returns a position as a `Fraction`.

## Tests

```
python -m unittest discover -s tests
```

Every operation is checked against a brute-force parent/children model on random trees, including random sequences of deletes and moves.

## Benchmarks

```
python benchmarks/bench.py            # trees of 10,000 and 100,000 nodes
python benchmarks/bench.py --quick    # a few seconds
python benchmarks/bench.py 1000000    # custom sizes
```

The script prints Markdown tables: build time and renumbering counts per tree shape (random, chain, star at the root, star at an inner node, alternating worst case), list growth at either end, and timings for `can_reach`, `depth`, `delete`, `cut_n_paste` and `delete_subtree`. Each `DList` keeps the counters `renumber_count` and `renumber_moved`, so the same figures are available in your own code via `t.Q1` and `t.Q2`.

## Provenance

Design and API: Enis Olgac. This Python port was written with Claude (Anthropic) from the C# original and the API reference.
