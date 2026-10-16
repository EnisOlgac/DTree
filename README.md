# DTree—Topology and Structure of Directed Trees: An Incremental Encoding

[![build](https://github.com/EnisOlgac/DTree/actions/workflows/build.yml/badge.svg)](https://github.com/EnisOlgac/DTree/actions/workflows/build.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23395710.svg)](https://doi.org/10.5281/zenodo.23395710)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE.md)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0009--7560--6107-a6ce39.svg)](https://orcid.org/0009-0009-7560-6107)

`DTree` is a minimal library for single-rooted directed trees whose structure is encoded by two linear projections, `Q1` and `Q2`. Reachability between any two nodes is answered by comparing their positions, without traversing the tree.

The reference implementation is in Python ([`python/`](python/)), with no dependencies and a test suite. The C# implementation and a WPF viewer are in [`csharp/`](csharp/).

## Projection Model

Each tree is encoded by two orderings of its nodes, both bracketed by the symbolic markers `[` (Source) and `]` (Sink):

- `Q1`—pre-order, children left to right
- `Q2`—pre-order, children right to left (sibling-reversed)

Node *u* can reach node *v* if and only if *u* strictly precedes *v* in both `Q1` and `Q2`. Reachability is irreflexive: no node reaches itself.

Inserting the edge (*u*, *v*) places *v* immediately after *u* in `Q2`, and at the end of *u*'s subtree in `Q1`.

## Background and Prior Art

`Q1` is the pre-order of a left-to-right depth-first traversal; `Q2` is the reversed post-order of the same traversal (equivalently, the pre-order with siblings right to left). That ancestry in a tree can be decided by comparing pre- and post-order positions is classical (Dietz, 1982). Maintaining positions in a list under insertions is the order-maintenance problem (Dietz & Sleator, 1987; Bender, Cole, Demaine, Farach-Colton & Zito, 2002); the Python implementation uses rational positions instead (see below) and borrows the density rule of Bender et al. for its rare renumbering.

What `DTree` contributes (see the [paper](#paper)) is maintaining both orderings incrementally with a priori known insertion points: a new child is always the last child of its parent in `Q1` (placed before the parent's delimiter) and the first child in `Q2` (placed directly after the parent). Every structural change is therefore local to both lists, and no traversal ever has to be recomputed.

- P. F. Dietz. Maintaining order in a linked list. *STOC 1982*, 122–127.
- P. F. Dietz, D. D. Sleator. Two algorithms for maintaining order in a list. *STOC 1987*, 365–372.
- M. A. Bender, R. Cole, E. D. Demaine, M. Farach-Colton, J. Zito. Two simplified algorithms for maintaining order in a list. *ESA 2002*, LNCS 2461, 152–164.

### Positions in the Python implementation

Positions are fractions, an idea of the author. A new node gets the *mediant* (a+c)/(b+d) of its neighbors a/b and c/d (the Stern–Brocot construction), which always lies strictly between them, so inserting a node normally moves no other node. Repeated insertion into the same gap—a node with many children, or growth at either end of a list—keeps positions at O(log n) bits: 17 bits for a star of 100,000 children. Only insertions that alternate between the two halves of a gap make denominators grow (like Fibonacci numbers); when one would exceed 64 bits, a small surrounding region is renumbered with simple fractions k/2³², larger regions being required to be sparser, as in Bender et al. See `python/benchmarks/` and the [changelog](CHANGELOG.md) for measurements.

## Key Features

- Single-rooted directed tree; no aliasing, no duplicate nodes
- Reachability check in O(1) via positions in `Q1` and `Q2`
- Dynamic operations: `insert`, `delete` (children move up), `delete_subtree`, `cut_n_paste` (move a subtree)
- Structural queries: ancestry, depth, paths, subtrees
- Set queries in O(1) or O(log k) via constructed nodes VMin, VMax, UMin and UMax (see below)
- No limit on tree depth or width

## Set Queries

Questions about a set of nodes *S* reduce to comparisons with a *constructed node*, an idea of the author (E. Olgac, "Topology and Structure of Directed Graphs - Inducing a Subgraph," 2021): the minimum or the maximum of each index over *S*, taken separately in `Q1` and `Q2`. The two values usually come from two different members, so the constructed node is no real node, but it is compared like one. Its name says which role *S* plays in `can_reach(u, v)`: *V* when *S* is the target, *U* when *S* is the source.

| question | constructed node | test | exact? |
| --- | --- | --- | --- |
| *u* reaches all of *S* | VMin | *u* left of VMin in both lists | yes, O(1) |
| *u* reaches some of *S* | VMax | *u* left of VMax in both lists | necessary only; exact in O(log k) |
| all of *S* reach *v* | UMax | *v* right of UMax in both lists | yes, O(1) |
| some of *S* reach *v* | UMin | *v* right of UMin in both lists | necessary only; exact in O(log k) |

For the two "some" questions the constructed node only rejects quickly. The exact answers use the order of the members in `Q1`: the subtree of *u* is the block directly after *u* in `Q1`, so *u* reaches some member exactly when the first member after *u* does; and *v* is reached by some member exactly when the last *topmost* member before *v* (one with no ancestor in *S*) reaches it.

```python
t.insert("A", "D")             # the Quick Start tree, plus D under A
t.vmin(["C", "D"]).reaches_all("A")        # True: A reaches C and D
t.vmin(["C", "D"]).reaches_all("B")        # False: B reaches C only
t.vmax(["C", "D"]).reaches_some("B")       # True
t.umax(["A", "B"]).reached_by_all("C")     # True: A and B both reach C
t.umin(["B", "D"]).reached_by_some("C")    # True: B reaches C
```

In C#: `t.VMin(nodes).ReachesAll(u)`, `t.VMax(nodes).ReachesSome(u)`, `t.UMax(nodes).ReachedByAll(v)`, `t.UMin(nodes).ReachedBySome(v)`, with names or node handles; `MayReachSome` and `MayBeReachedBySome` are the O(1) filters. A constructed node stores its members, not positions; since insertions keep the order of existing nodes, it stays valid while the tree grows, and after a deletion or a move it is recomputed on its next use. A classical tree with parent and child links answers the same questions by climbing towards the root. See [`docs/set-queries.md`](docs/set-queries.md).

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

## C# Implementation

[`csharp/DTree.Core/`](csharp/DTree.Core/) is a C# (.NET 9) port of the Python implementation with the same API in C# naming: `Insert`, `Delete`, `DeleteSubtree`, `CutNPaste`, `CanReach`, `PathToRoot`, `Depth`, …, and `Q1`/`Q2` as `DList` projections with rational positions. Its test program checks every query against a brute-force model, as the Python tests do:

```
dotnet run --project csharp/DTree.Tests -c Release            # tests
dotnet run --project csharp/DTree.Tests -c Release -- bench   # benchmarks
```

```csharp
using DirectedTrees;

var t = new DTree("P1");
t.Insert("A", "B");
t.Insert("B", "C");
t.CanReach("A", "C");   // true
t.PathToRoot("C");      // ["C", "B", "A"]

// Node handles skip the lookup by name:
DNode a = t.GetNode("A"), c = t.GetNode("C");
t.CanReach(a, c);       // true, two position comparisons
DNode d = t.Insert(a, "D");
```

[`csharp/Tree.View/`](csharp/Tree.View/) is a WPF viewer (Windows only) built on `DTree.Core`: *Select DiTree* opens a `.csx` file from [`examples/`](examples/), lists the inserted edges, and draws the tree once along `Q1` and once along `Q2`. Open `csharp/DTree.sln` in Visual Studio and start `Tree.View`.

## Original C# Prototype

The author's original C# prototype (with the WPF viewer on top of it) is included in the releases up to version 1.1.0 and archived on Zenodo (version 1.1.0: [10.5281/zenodo.23397159](https://doi.org/10.5281/zenodo.23397159)). It was removed from the repository afterwards; `DTree.Core` replaces it.

## Documentation

- [API reference (Markdown)](docs/API.md)
- [Set queries with constructed nodes](docs/set-queries.md)—with a comparison to classical doubly linked trees
- [API reference (PDF)](docs/User.Doc.pdf)—LaTeX source: [`docs/User.Doc.tex`](docs/User.Doc.tex)

## Repository Layout

```
DTree/
├── python/         Python implementation with tests
├── csharp/         C# implementation (DTree.Core, DTree.Tests) and WPF viewer
│                   (Tree.View)
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

To cite the software itself, use its Zenodo archive: E. Olgac, *DTree—Topology and Structure of Directed Trees: An Incremental Encoding*, version 1.4.0, Zenodo, 2026. doi: [10.5281/zenodo.23420472](https://doi.org/10.5281/zenodo.23420472) (all versions: [10.5281/zenodo.23395710](https://doi.org/10.5281/zenodo.23395710)).

## License

This project is released under the MIT License. See [`LICENSE.md`](LICENSE.md) for details.

## Author

Enis Olgac · [ORCID 0009-0009-7560-6107](https://orcid.org/0009-0009-7560-6107) · [github.com/EnisOlgac](https://github.com/EnisOlgac) · enis@digraphs.info

The Python implementation was written with Claude (Anthropic) from the C# prototype and the API reference.
