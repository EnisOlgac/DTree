# DTree—Directed Tree Library for Symbolic Structure

[![build](https://github.com/EnisOlgac/DTree/actions/workflows/build.yml/badge.svg)](https://github.com/EnisOlgac/DTree/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE.md)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0009--7560--6107-a6ce39.svg)](https://orcid.org/0009-0009-7560-6107)

`DTree` is a minimal library for single-rooted directed trees whose structure is encoded by two linear projections, `Q1` and `Q2`. Reachability between any two nodes is answered by comparing their positions, without traversing the tree.

The reference implementation is in Python ([`python/`](python/)), with no dependencies and a test suite. The original C# prototype is in [`src/`](src/).

## Projection Model

Each tree is encoded by two orderings of its nodes, both bracketed by the symbolic markers `[` (Source) and `]` (Sink):

- `Q1`—pre-order, children left to right
- `Q2`—pre-order, children right to left (sibling-reversed)

Node *u* can reach node *v* if and only if *u* strictly precedes *v* in both `Q1` and `Q2`. Reachability is irreflexive: no node reaches itself.

Inserting the edge (*u*, *v*) places *v* immediately after *u* in `Q2`, and at the end of *u*'s subtree in `Q1`.

## Background and Prior Art

`Q1` is the pre-order of a left-to-right depth-first traversal; `Q2` is the reversed post-order of the same traversal (equivalently, the pre-order with siblings right to left). That ancestry in a tree can be decided by comparing pre- and post-order positions is classical (Dietz, 1982). Maintaining positions in a list under insertions is the order-maintenance problem (Dietz & Sleator, 1987; Bender, Cole, Demaine, Farach-Colton & Zito, 2002); the Python implementation uses the latter scheme for its positions.

What `DTree` contributes (see the [paper](#paper)) is maintaining both orderings incrementally with a priori known insertion points: a new child is always the last child of its parent in `Q1` (placed before the parent's delimiter) and the first child in `Q2` (placed directly after the parent). Every structural change is therefore local to both lists, and no traversal ever has to be recomputed.

- P. F. Dietz. Maintaining order in a linked list. *STOC 1982*, 122–127.
- P. F. Dietz, D. D. Sleator. Two algorithms for maintaining order in a list. *STOC 1987*, 365–372.
- M. A. Bender, R. Cole, E. D. Demaine, M. Farach-Colton, J. Zito. Two simplified algorithms for maintaining order in a list. *ESA 2002*, LNCS 2461, 152–164.

## Key Features

- Single-rooted directed tree; no aliasing, no duplicate nodes
- Reachability check in O(1) via positions in `Q1` and `Q2`
- Dynamic operations: `insert`, `delete` (children move up), `delete_subtree`, `cut_n_paste` (move a subtree)
- Structural queries: ancestry, depth, paths, subtrees
- No limit on tree depth or width

## Quick Start (Python)

```python
import sys; sys.path.insert(0, "python")
from dtree import DTree

t = DTree("P1")
t.insert("A", "B")
t.insert("B", "C")

t.can_reach("A", "C")   # True
t.path_to_root("C")     # ['C', 'B', 'A']
t.q1, t.q2              # (['A', 'B', 'C'], ['A', 'B', 'C'])
```

Load a sample tree (`parent: child1; child2` per line):

```python
t = DTree.from_file("examples/Test.csx")
```

See [`python/README.md`](python/README.md) for the full API and semantics. Run the tests with:

```
cd python
python -m unittest discover -s tests
```

## C# Prototype

[`src/`](src/) contains the original C# implementation (`Tree` library, .NET 9) and `Tree.View`, a WPF viewer that draws a tree from a `.csx` file (Windows only). Insertion and the `Q1`/`Q2` projections work as described above. Known issues in the prototype:

- `CutNPaste` and `Delete` are not yet implemented.
- `Root`, `PathToRoot`, `RootPathTo`, `Depth`, `IsAncestor`, `IsDescendant` and `SameSubtree` do not yet match the API reference.
- `CanReach(u, u)` returns `true` (reflexive), unlike the Python implementation.
- Projection positions are `decimal` midpoints rounded to the leading significant digit of the gap, which keeps positions short. With no renumbering, though, a gap that keeps receiving insertions still shrinks geometrically and runs out of `decimal` precision at roughly 65 nodes in a chain or about 110 children under one node.

## Documentation

- [API reference (Markdown)](docs/API.md)
- [API reference (PDF)](docs/User.Doc.pdf)—LaTeX source: [`docs/User.Doc.tex`](docs/User.Doc.tex)

## Repository Layout

```
DTree/
├── python/         Python implementation with tests
├── src/            C# prototype (Tree library, Tree.View WPF viewer)
├── examples/       sample trees (.csx: "parent: child1; child2")
├── docs/           API reference (Markdown, PDF, LaTeX sources)
├── CITATION.cff    citation metadata
├── LICENSE.md      MIT License
└── README.md
```

## Paper

The method is described in:

> E. Olgac, "Topology and Structure of Directed Trees: An Incremental Encoding," *Artificial Intelligence*. IntechOpen, Dec. 11, 2025. doi: [10.5772/intechopen.1013408](https://doi.org/10.5772/intechopen.1013408).

## Citing

If you use `DTree` in academic work, please cite the paper above. GitHub's "Cite this repository" button in the sidebar shows it, using the metadata in [`CITATION.cff`](CITATION.cff).

## License

This project is released under the MIT License. See [`LICENSE.md`](LICENSE.md) for details.

## Author

Enis Olgac · [ORCID 0009-0009-7560-6107](https://orcid.org/0009-0009-7560-6107) · [github.com/EnisOlgac](https://github.com/EnisOlgac) · enis@digraphs.info

The Python implementation was written with Claude (Anthropic) from the C# prototype and the API reference.
