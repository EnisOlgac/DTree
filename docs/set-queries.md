# Set Queries with Constructed Nodes

Many questions about a tree concern a set of nodes rather than a single one: does *u* reach all of them, or some of them? Is *v* reached by all of them, or by some? `DTree` answers each of these with one comparison against a *constructed node*, with no climbing through the tree. This page explains the idea, shows where it is exact and where it only filters, and compares it with the classical representation of a tree by parent and child links.

The constructed node and the names VMin and VMax are Enis Olgac's, from his presentation "Topology and Structure of Directed Graphs - Inducing a Subgraph" (ResearchGate, May 2021). The naming by role with UMin and UMax is his as well. The two exact tests for "some" (sections 4 and 5) were added by Claude for release 1.4.0.

## 1. Positions and reachability

Every node *x* has a position in each projection; write it as the pair (Q1(*x*), Q2(*x*)). Node *u* reaches node *v* if and only if

> Q1(*u*) < Q1(*v*) and Q2(*u*) < Q2(*v*),

that is, *u* lies left of *v* in both lists. Reachability is irreflexive.

A running example: a root *r* with three children *a*, *m*, *b*, numbered by their places in the lists:

| node | Q1 | Q2 | (Q1, Q2) |
| --- | ---: | ---: | --- |
| r | 0 | 0 | (0, 0) |
| a | 1 | 3 | (1, 3) |
| m | 2 | 2 | (2, 2) |
| b | 3 | 1 | (3, 1) |

Only *r* reaches anything here; the three children are siblings.

## 2. Constructed nodes

For a set *S*, take the minimum of each index over *S*, separately in Q1 and in Q2—or the maximum. For *S* = {*a*, *b*}:

- minimum: (min(1, 3), min(3, 1)) = (1, 1), with the 1 in Q1 from *a* and the 1 in Q2 from *b*
- maximum: (max(1, 3), max(3, 1)) = (3, 3), with the 3 in Q1 from *b* and the 3 in Q2 from *a*

The two values usually come from two different members, so no real node sits at (1, 1) or (3, 3). Still, the pair can be compared with any node exactly like a node. That is the *constructed node*.

Which one to use depends on the role *S* plays in can_reach(*u*, *v*):

| *S* as | constructed node | question | test | exact? |
| --- | --- | --- | --- | --- |
| target, can_reach(*u*, *S*) | VMin | *u* reaches **all** of *S* | *u* left of VMin in both lists | yes |
| target, can_reach(*u*, *S*) | VMax | *u* reaches **some** of *S* | *u* left of VMax in both lists | necessary only |
| source, can_reach(*S*, *v*) | UMax | **all** of *S* reach *v* | *v* right of UMax in both lists | yes |
| source, can_reach(*S*, *v*) | UMin | **some** of *S* reach *v* | *v* right of UMin in both lists | necessary only |

UMin and VMin hold the same numbers, as do UMax and VMax; only the role differs, and the name makes the direction visible in the code.

## 3. "All" is exact, "some" only filters

**All.** *u* lies left of every member in Q1 exactly when it lies left of the smallest Q1 index among them, and the same holds for Q2. So *u* reaches every member of *S* exactly when it lies left of VMin in both lists. In the example, *r* = (0, 0) is left of (1, 1) and indeed reaches *a* and *b*. The argument for UMax is the mirror image.

**Some.** If *u* reaches some member *s*, then *u* is left of *s* in both lists, hence left of the maximum in both lists: lying left of VMax is necessary. It is not sufficient, because the maximum combines the "good" coordinate of two different members. In the example with *S* = {*a*, *b*}:

- VMax = (3, 3), and *m* = (2, 2) lies left of it in both lists—yet *m* reaches neither *a* (2 < 1 fails) nor *b* (2 < 3 holds, but 2 < 1 fails).
- UMin = (1, 1), and *m* = (2, 2) lies right of it in both lists—yet neither *a* (3 < 2 fails) nor *b* (3 < 2 fails) reaches *m*.

So for "some" the constructed node rejects quickly (`may_reach_some`, `may_be_reached_by_some`), and an exact test needs a little more.

## 4. Exact: *u* reaches some of *S*

The subtree of *u* is the contiguous block of Q1 directly after *u*. If *u* reaches any member, then the first member after *u* in Q1 lies in that block—every member before the end of the block is inside it. So:

1. keep the members sorted by Q1 (binary insertion when a member is added);
2. find the first member after *u* in Q1 by binary search;
3. test that one member with can_reach.

That is O(log *k*) for *k* members, after the O(1) rejection by VMax.

## 5. Exact: some of *S* reach *v*

Here the last member before *v* in Q1 is not enough: a member nested below an ancestor of *v* can lie between that ancestor and *v* without reaching *v* itself. The remedy is to keep only the **topmost** members—those with no ancestor in *S*. Their subtrees are disjoint, so if one of them is an ancestor of *v*, no other topmost member lies between it and *v* in Q1. So:

1. keep the topmost members sorted by Q1 (when a member is added, it is dropped if a topmost member already reaches it; otherwise it replaces the topmost members it reaches, which follow it directly in Q1);
2. find the last topmost member before *v* in Q1 by binary search;
3. test that one member with can_reach.

Again O(log *k*), after the O(1) rejection by UMin. Some of *S* reach *v* if and only if some topmost member does, since every member lies below a topmost one.

## 6. Constructed nodes under changes

A constructed node stores its members—and for each list the member holding the extreme index—never the numbers themselves. Insertions and renumbering keep the order of existing nodes, so a constructed node stays valid while the tree grows, with no work at all. Deleting nodes or moving a subtree with `cut_n_paste` can change which member is extreme; after such an operation the constructed node is recomputed from its remaining members on its next use, in O(*k* log *k*).

## 7. Comparison with classical doubly linked trees

The classical representation keeps, for every node, a link to its parent and a list of its children. Reachability is then answered by climbing: *u* reaches *v* if *u* appears on the path from *v* up to the root. That costs O(depth) per question, and set questions multiply it:

| question | parent walk | DTree |
| --- | --- | --- |
| *u* reaches *v* | climb from *v*: O(depth) | two comparisons: O(1) |
| *u* reaches all / some of *S* | climb from every member: O(*k* · depth) | O(1) / O(log *k*) |
| all / some of *S* reach *v* | climb once from *v*, look each ancestor up in a hash set of *S*: O(depth) | O(1) / O(log *k*) |

There is no counterpart of the constructed node in the linked representation: a combination of "the smallest Q1 of one member with the smallest Q2 of another" has no meaning without the two orders. A classical program can obtain the same power only by computing such orders itself—pre- and post-order numbers from a traversal (Dietz, 1982), or ancestor tables for lowest-common-ancestor queries—and those are static: after an insertion they must be recomputed or repaired. `DTree` maintains both orders incrementally, with the insertion points known in advance, so the numbers are always current.

The price is paid at insertion: a new node takes two list insertions with mediant positions instead of one parent link. The benchmarks in the [changelog](../CHANGELOG.md) show the build times; for single queries on shallow trees the parent walk is as fast as DTree or faster (see below).

## 8. Measurements

Measured by Enis Olgac on his NUC (Windows) with Python 3.14.2 and .NET 9.0.21. Each tree has 100,000 nodes: a chain ("spine") of the given depth, with all other nodes attached at random to spine nodes. Every answer of DTree was checked against the parent walk.

### Single reachability queries

Random pairs of nodes; C# with node handles.

| depth | Python: DTree | Python: parent walk | factor | C#: DTree | C#: parent walk | factor |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 1.45 µs | 0.59 µs | 0.4× | 0.047 µs | 0.034 µs | 0.7× |
| 100 | 1.41 µs | 1.90 µs | 1.3× | 0.048 µs | 0.105 µs | 2.2× |
| 1,000 | 1.45 µs | 14.4 µs | 10× | 0.046 µs | 1.28 µs | 28× |
| 10,000 | 1.27 µs | 178 µs | 140× | 0.050 µs | 17.1 µs | 344× |
| 100,000 | 1.36 µs | 3,813 µs | 2,811× | 0.054 µs | 657 µs | 12,066× |

DTree's time does not depend on depth; the parent walk's grows with it. On shallow trees the walk wins, since it only takes a few steps.

### Set queries

A set of 1,000 random nodes. Python: 200 random query nodes for both sides. C#: DTree answered 100,000 random query nodes and the parent walk 200 (both checked on those 200); with fewer DTree queries the measurement is too short and too cache-friendly to be meaningful.

| depth | question | Python: DTree | Python: walk | factor | C#: DTree | C#: walk | factor |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | reaches all | 1.14 µs | 0.7 µs | 0.6× | 0.114 µs | 0.1 µs | 1.2× |
| 10 | reaches some | 4.99 µs | 285 µs | 57× | 0.286 µs | 39.9 µs | 140× |
| 10 | reached by all | 1.31 µs | 0.6 µs | 0.5× | 0.041 µs | 0.2 µs | 4.2× |
| 10 | reached by some | 5.41 µs | 0.4 µs | 0.1× | 0.272 µs | 0.1 µs | 0.5× |
| 100 | reaches all | 1.21 µs | 0.9 µs | 0.7× | 0.026 µs | 0.4 µs | 15× |
| 100 | reaches some | 6.08 µs | 1,577 µs | 260× | 0.313 µs | 222 µs | 710× |
| 100 | reached by all | 1.12 µs | 2.1 µs | 1.9× | 0.044 µs | 3.1 µs | 69× |
| 100 | reached by some | 5.09 µs | 2.0 µs | 0.4× | 0.272 µs | 3.3 µs | 12× |
| 1,000 | reaches all | 1.57 µs | 8.6 µs | 5.5× | 0.027 µs | 3.8 µs | 141× |
| 1,000 | reaches some | 7.92 µs | 14,644 µs | 1,849× | 0.268 µs | 1,633 µs | 6,099× |
| 1,000 | reached by all | 1.64 µs | 25.1 µs | 15× | 0.058 µs | 8.3 µs | 144× |
| 1,000 | reached by some | 5.33 µs | 21.2 µs | 4.0× | 0.141 µs | 6.7 µs | 48× |
| 10,000 | reaches all | 1.41 µs | 356 µs | 252× | 0.028 µs | 48.6 µs | 1,745× |
| 10,000 | reaches some | 7.79 µs | 172,536 µs | 22,141× | 0.209 µs | 17,018 µs | 81,448× |
| 10,000 | reached by all | 1.81 µs | 278 µs | 154× | 0.029 µs | 63.9 µs | 2,173× |
| 10,000 | reached by some | 3.31 µs | 283 µs | 86× | 0.126 µs | 56.7 µs | 450× |

Building all four constructed nodes for the 1,000 members took 0.90 ms in C#, once per set.

Reading the table:

- "Reaches some" is the hardest case for the parent walk, which must climb from every member: O(*k* · depth). DTree answers it in O(log *k*).
- For "reached by", the parent walk climbs only once, from *v*, and stays competitive on shallow trees; in Python it wins at depths 10 and 100. From depth 1,000 on, DTree is ahead in both languages.
- Parent-walk times below 1 µs in C# are rounded to 0.1 µs; the factors are computed from the unrounded values.

### Reproducing

```
python python/benchmarks/bench.py                              # full run
python python/benchmarks/bench.py --quick                      # a few seconds
dotnet run --project csharp/DTree.Tests -c Release -- bench
```

## References

- E. Olgac, "Topology and Structure of Directed Graphs - Inducing a Subgraph," presentation, ResearchGate, May 2021.
- E. Olgac, "Topology and Structure of Directed Trees: An Incremental Encoding," *Artificial Intelligence*, IntechOpen, 2025. doi: [10.5772/intechopen.1013408](https://doi.org/10.5772/intechopen.1013408).
- P. F. Dietz, "Maintaining order in a linked list," *STOC 1982*, 122–127.
