# Changelog

## 1.2.0

**C# implementation** (`csharp/DTree.Core`): a port of the Python 1.1.0 implementation with the same API in C# naming and the same rational (mediant) positions, stored as 64-bit numerator/denominator pairs and compared with 128-bit products. A test program (`csharp/DTree.Tests`) mirrors the Python test suite and includes the benchmark (`-- bench`). The automatic checks now also run the C# tests.

**Viewer on the new library:** the WPF viewer (`csharp/Tree.View`) now uses `DTree.Core` instead of the prototype. Invalid lines in a `.csx` file are reported and skipped instead of stopping the program. `DTree.Core` and `DTree.Tests` are part of `csharp/DTree.sln`. The original prototype (`src/Tree`) has been removed from the repository; it remains available in releases 1.0.0 and 1.1.0 and their Zenodo archives.

**Folder renamed:** the C# code moved from `src/` to `csharp/`.

**Title** aligned with the paper: "DTree—Topology and Structure of Directed Trees: An Incremental Encoding".

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
