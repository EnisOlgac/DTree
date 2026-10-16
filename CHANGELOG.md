# Changelog

## 1.3.0

Archived on Zenodo: doi:10.5281/zenodo.23414463.

**Node handles in C#** (`DTree.Core`): `Insert` now returns a `DNode` handle, and every operation also accepts handles (`Insert(DNode, string)`, `CanReach(DNode, DNode)`, `Delete`, `DeleteSubtree`, `CutNPaste`, `IsRoot`, `IsLeaf`, `Depth`, …; `GetNode(name)` and `TryGetNode` give the handle of a named node). A handle refers directly to the node's positions in Q1 and Q2, so a reachability test on handles is two position comparisons with no lookup by name. Inside `DTree`, parents and children are kept as direct references, too; names are only looked up where a method receives a name. The idea of using addresses as ids comes from Enis Olgac's original implementation. Handles of deleted nodes, or of another tree, are rejected or reported as unreachable. The name-based API is unchanged.

Reachability on a random tree of 100,000 nodes, 1,000,000 queries (`dotnet run --project csharp/DTree.Tests -c Release -- bench 10000 100000`, same Windows PC as for 1.2.0):

| `CanReach` per call | 1.2.0 | 1.3.0 |
| --- | ---: | ---: |
| C#, with names | 0.369 µs | 0.181 µs |
| C#, with node handles | — | 0.085 µs |
| Python 1.2.0 / 1.3.0, with names (for comparison) | 1.4 µs | 1.4 µs |

With names, `CanReach` now does two dictionary lookups instead of six; with handles it does none, which makes it about 4× faster than in 1.2.0 and about 16× faster than the Python implementation. Building trees takes as long as in 1.2.0 (random tree of 100,000 nodes: 0.24 s), since every new node is still registered by name; renumbering counts are unchanged.

## 1.2.0

Archived on Zenodo: doi:10.5281/zenodo.23414087.

**C# implementation** (`csharp/DTree.Core`): a port of the Python 1.1.0 implementation with the same API in C# naming and the same rational (mediant) positions, stored as 64-bit numerator/denominator pairs and compared with 128-bit products. A test program (`csharp/DTree.Tests`) mirrors the Python test suite and includes the benchmark (`-- bench`). The automatic checks now also run the C# tests.

**Viewer on the new library:** the WPF viewer (`csharp/Tree.View`) now uses `DTree.Core` instead of the prototype. Invalid lines in a `.csx` file are reported and skipped instead of stopping the program. `DTree.Core` and `DTree.Tests` are part of `csharp/DTree.sln`. The original prototype (`src/Tree`) has been removed from the repository; it remains available in releases 1.0.0 and 1.1.0 and their Zenodo archives.

**Folder renamed:** the C# code moved from `src/` to `csharp/`.

**Title** aligned with the paper: "DTree—Topology and Structure of Directed Trees: An Incremental Encoding".

**Benchmark, Python and C#** (`python python/benchmarks/bench.py 10000 100000` and `dotnet run --project csharp/DTree.Tests -c Release -- bench 10000 100000`, trees of 100,000 nodes, both on the same Windows PC with Python 3.14.2 and .NET 9.0.21):

| shape | build time Python [s] | build time C# [s] | factor | renumberings Q1 / Q2, Python | renumberings Q1 / Q2, C# | positions moved per insertion, Python / C# |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| random | 0.45 | 0.235 | 1.9× | 0 / 0 | 0 / 0 | 0 / 0 |
| chain | 0.25 | 0.189 | 1.3× | 0 / 0 | 0 / 0 | 0 / 0 |
| star (root) | 0.21 | 0.107 | 2.0× | 0 / 0 | 0 / 0 | 0 / 0 |
| star (inner node) | 0.37 | 0.127 | 2.9× | 0 / 0 | 0 / 0 | 0 / 0 |
| alternating (worst case) | 0.56 | 0.294 | 1.9× | 0 / 2,172 | 0 / 3,447 | 3.83 / 4.44 |

| query on a random tree of 100,000 nodes | Python | C# | factor |
| --- | ---: | ---: | ---: |
| `can_reach` / `CanReach`, per call | 1.4 µs | 0.37 µs | 3.8× |

Both implementations renumber identically except in the alternating worst case: C# stores positions as 64-bit numerator/denominator pairs and therefore renumbers somewhat earlier (denominators up to 2^40, renumbered regions use k/2^20) than Python with its unbounded integers (2^64 and k/2^32). The C# figures match those predicted by running the Python implementation with the C# limits. Building a tree is dominated by dictionary lookups on node names in both languages, so C# gains less there than on reachability queries, which compare positions directly.

## 1.1.0

Archived on Zenodo: doi:10.5281/zenodo.23397159.

**Rational positions in `DList`** (Python). Positions in Q1 and Q2 are now fractions. A new node gets the mediant (a+c)/(b+d) of its two neighbors, so inserting normally moves no other node. Rational positions were Enis Olgac's idea; the mediant construction, the fallback renumbering and the measurements were done with Claude (Anthropic).

Benchmark (`python benchmarks/bench.py 10000 100000`, trees of 100,000 nodes, same machine):

| shape | renumberings Q1 / Q2, 1.0.0 | renumberings Q1 / Q2, 1.1.0 | positions moved per insertion, 1.0.0 → 1.1.0 |
| --- | ---: | ---: | ---: |
| random | 0 / 0 | 0 / 0 | 0 → 0 |
| chain | 0 / 0 | 0 / 0 | 0 → 0 |
| star (root) | 0 / 13,764 | 0 / 0 | 5.53 → 0 |
| star (inner node) | 13,035 / 13,763 | 0 / 0 | 10.78 → 0 |
| alternating (worst case) | 0 / 13,072 | 0 / 2,172 | 5.84 → 3.83 |

Largest numerator or denominator at 100,000 nodes: 17–18 bits for chains and stars, 35 bits for random trees, 60 bits for the alternating worst case. `can_reach` costs about the same (2.5 → 2.7 µs per call; two multiplications instead of one integer comparison).

Other changes since 1.0.0:

- `DList.index(v)` returns a `Fraction` (SOURCE and SINK: −∞ and +∞).
- `python/benchmarks/bench.py`, with an alternating worst-case shape, and the counters `DList.renumber_count` and `DList.renumber_moved`.
- New tests: stars without renumbering, the alternating worst case, and 20,000 random list operations against a plain Python list.
- README: Zenodo DOIs, paper reference, background on positions.

## 1.0.0

First public release: Python implementation (insert, delete, delete_subtree, cut_n_paste, queries), C# prototype with WPF viewer, API reference. Archived on Zenodo: doi:10.5281/zenodo.23395711.
