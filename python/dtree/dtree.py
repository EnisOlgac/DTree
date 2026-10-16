"""DTree: a single-rooted directed tree encoded by two linear projections.

Python implementation of the DTree design and API by Enis Olgac (original C#
prototype in releases up to 1.1.0). This port was written with Claude (Anthropic) and checked against a
brute-force reference in ``tests/``.

Projection model
----------------
Every tree is encoded by two orderings of its nodes, both bracketed by the
symbolic markers SOURCE ("[") and SINK ("]"):

* Q1: pre-order, children left to right (in insertion order).
* Q2: pre-order, children right to left (sibling-reversed).

Node u reaches node v if and only if u strictly precedes v in both Q1 and Q2.
Reachability is irreflexive: no node reaches itself.

Update rules (taken from the C# original)
----------------------------------------
* insert(u, v): v is placed immediately after u in Q2, and in Q1 immediately
  before the first node after u that u cannot reach (the end of u's subtree).
  Insertion costs O(depth of the subtree below u); positions of other nodes
  normally stay unchanged.
* delete(v): v is removed from both projections; its children move up to v's
  parent and keep their relative order (a cut-and-paste of v's children).
* delete_subtree(v): the contiguous block of v's subtree is removed from both
  projections.
* cut_n_paste(u, p): the contiguous block of u's subtree is lifted out of both
  projections and re-inserted under p using the same rule as insert.

Positions are fractions. A new node gets the mediant (a+c)/(b+d) of its two
neighbors a/b and c/d (the Stern-Brocot construction), which always lies
strictly between them, so normally no other node moves. Rational positions
were Enis Olgac's idea; repeated insertion into the same gap (a node with many
children, appending at either end) then keeps positions at O(log n) bits. Only
when a denominator would exceed 64 bits, which needs alternating insertions,
is a small surrounding region renumbered with simple fractions k/2**32.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Dict, Iterable, Iterator, List, Optional

SOURCE = "["
SINK = "]"

_Q = 1 << 32  # denominator used when a crowded region is renumbered
_LIMIT = 64  # renumber when a denominator would exceed this many bits
_SLACK = 16  # after renumbering, neighbors are at least this many 1/_Q apart
_GROWTH = 2  # each doubling of the region raises the required spacing by this factor


class _Cell:
    __slots__ = ("name", "prev", "next", "num", "den")

    def __init__(self, name: str) -> None:
        self.name = name
        self.prev: Optional[_Cell] = None
        self.next: Optional[_Cell] = None
        self.num = 0
        self.den = 1


class DList:
    """Doubly linked list with rational positions (O(1) precedence test).

    Positions are fractions num/den. A new node gets the mediant
    (a+c)/(b+d) of its neighbors a/b and c/d, which always lies strictly
    between them; SOURCE and SINK act as -1/0 and +1/0. Nothing else moves.
    Only when a denominator would exceed _LIMIT bits is a small surrounding
    region renumbered with simple fractions k/_Q.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._cells: Dict[str, _Cell] = {}
        self.first = self._new(SOURCE)
        self.last = self._new(SINK)
        self.first.next = self.last
        self.last.prev = self.first
        self.first.num, self.first.den = -1, 0  # -infinity
        self.last.num, self.last.den = 1, 0  # +infinity
        # Statistics: how often positions were renumbered and how many moved.
        self.renumber_count = 0
        self.renumber_moved = 0

    # -- internals --------------------------------------------------------
    def _new(self, name: str) -> _Cell:
        cell = _Cell(name)
        self._cells[name] = cell
        return cell

    @staticmethod
    def _lt(x: _Cell, y: _Cell) -> bool:
        """x lies strictly left of y, by comparing x.num/x.den with y.num/y.den."""
        if x.den and y.den:
            return x.num * y.den < y.num * x.den
        if x.den == 0 and y.den == 0:
            return x.num < y.num
        return (x.num if x.den == 0 else 0) < (y.num if y.den == 0 else 0)

    def _link_after(self, cell: _Cell, prev: _Cell) -> None:
        nxt = prev.next
        cell.prev, cell.next = prev, nxt
        prev.next = cell
        nxt.prev = cell
        if prev is self.first and nxt is self.last:
            cell.num, cell.den = 0, 1  # first node of an empty list
            return
        # Mediant of the neighbors. Next to SOURCE (-1/0) or SINK (+1/0) this
        # steps by one whole unit, so a list can grow at either end forever
        # without renumbering (positives to the right, negatives to the left).
        cell.num = prev.num + nxt.num
        cell.den = prev.den + nxt.den
        if cell.den.bit_length() > _LIMIT:
            self._rebalance(cell)

    def _rebalance(self, cell: _Cell) -> None:
        """Renumber the smallest region around ``cell`` that has room, using fractions k/_Q."""
        q = _Q
        lo = hi = cell
        m, k, need = 1, 1, _SLACK
        while True:
            for _ in range(k):
                if lo.prev is not self.first:
                    lo = lo.prev
                    m += 1
                if hi.next is not self.last:
                    hi = hi.next
                    m += 1
            left, right = lo.prev, hi.next
            if left is self.first and right is self.last:
                ks = [(j - m // 2) * q for j in range(m)]
                break
            if left is self.first:
                top = -((-right.num * q) // right.den)  # ceil(right * q)
                ks = [top - (m - j) * q for j in range(m)]
                break
            if right is self.last:
                bottom = (left.num * q) // left.den  # floor(left * q)
                ks = [bottom + (j + 1) * q for j in range(m)]
                break
            bottom = (left.num * q) // left.den
            top = -((-right.num * q) // right.den)
            room = top - bottom - 1  # integers k with left < k/q < right
            if room >= m * need:
                ks = [bottom + ((j + 1) * (room + 1)) // (m + 1) for j in range(m)]
                break
            # Larger regions must be sparser before they are accepted (as in
            # Bender et al.), so a renumbered region keeps spare room and the
            # next overflow nearby can again be handled locally.
            k *= 2
            need *= _GROWTH
        c = lo
        for kv in ks:
            c.num, c.den = kv, q
            c = c.next
        self.renumber_count += 1
        self.renumber_moved += m

    def _unlink(self, cell: _Cell) -> None:
        cell.prev.next = cell.next
        cell.next.prev = cell.prev
        cell.prev = cell.next = None

    # -- public -----------------------------------------------------------
    def __contains__(self, name: str) -> bool:
        return name in self._cells

    # Names follow List.cs: Source/Sink, First/Last, Prev/Next, Index,
    # IsAllocated, IsLeftOf ... IsSelfOrRightOf, InsAfter/InsBefore, IsSameAs.

    @property
    def source(self) -> str:
        return self.first.name

    @property
    def sink(self) -> str:
        return self.last.name

    def index(self, name: str):
        """Position of ``name`` as a Fraction (SOURCE/SINK: -inf/+inf), or None if absent (List.cs: Index)."""
        cell = self._cells.get(name)
        if cell is None:
            return None
        if cell.den == 0:
            return float("inf") if cell.num > 0 else float("-inf")
        return Fraction(cell.num, cell.den)

    label = index

    def is_allocated(self, name: str) -> bool:
        return name in self._cells

    def is_not_allocated(self, name: str) -> bool:
        return name not in self._cells

    def next(self, name: str) -> Optional[str]:
        nxt = self._cells[name].next
        return nxt.name if nxt else None

    def prev(self, name: str) -> Optional[str]:
        prv = self._cells[name].prev
        return prv.name if prv else None

    def is_left_of(self, v: str, u: str) -> bool:
        return self._lt(self._cells[v], self._cells[u])

    def is_self_or_left_of(self, v: str, u: str) -> bool:
        return v == u or self._lt(self._cells[v], self._cells[u])

    def is_right_of(self, v: str, u: str) -> bool:
        return self._lt(self._cells[u], self._cells[v])

    def is_self_or_right_of(self, v: str, u: str) -> bool:
        return v == u or self._lt(self._cells[u], self._cells[v])

    def precedes(self, u: str, v: str) -> bool:
        """Strict order: u lies left of v (same as is_left_of)."""
        x, y = self._cells[u], self._cells[v]
        if x.den and y.den:
            return x.num * y.den < y.num * x.den
        return self._lt(x, y)

    def _cell_for(self, name: str) -> _Cell:
        """Existing cell (unlinked first, so it is moved) or a new one."""
        cell = self._cells.get(name)
        if cell is None:
            return self._new(name)
        self._unlink(cell)
        return cell

    def insert_after(self, name: str, anchor: str) -> None:
        """Place ``name`` directly after ``anchor``; moves it if already present (List.cs: InsAfter)."""
        if name == anchor or name == SINK:
            return
        if anchor == SINK:
            return self.insert_before(name, SINK)
        a = self._cells[anchor]
        if a.next is not None and a.next.name == name:
            return
        cell = self._cell_for(name)
        self._link_after(cell, self._cells[anchor])

    def insert_before(self, name: str, anchor: str) -> None:
        """Place ``name`` directly before ``anchor``; moves it if already present (List.cs: InsBefore)."""
        if name == anchor or name == SOURCE:
            return
        if anchor == SOURCE:
            return self.insert_after(name, SOURCE)
        a = self._cells[anchor]
        if a.prev is not None and a.prev.name == name:
            return
        cell = self._cell_for(name)
        self._link_after(cell, self._cells[anchor].prev)

    def is_same_as(self, other: "DList") -> bool:
        """True if both lists hold the same nodes in the same order (List.cs: IsSameAs)."""
        return list(self) == list(other)

    def remove(self, name: str) -> None:
        self._unlink(self._cells.pop(name))

    def cut_block(self, first: str, last: str) -> List[str]:
        """Remove the contiguous block first..last and return its names in order."""
        a, b = self._cells[first], self._cells[last]
        names, cell = [], a
        while True:
            names.append(cell.name)
            if cell is b:
                break
            cell = cell.next
        a.prev.next = b.next
        b.next.prev = a.prev
        for n in names:
            self._cells.pop(n)
        return names

    def paste_block_after(self, names: List[str], anchor: str) -> None:
        for n in names:
            self.insert_after(n, anchor)
            anchor = n

    def __iter__(self) -> Iterator[str]:
        cell = self.first.next
        while cell is not self.last:
            yield cell.name
            cell = cell.next

    def to_list(self, with_markers: bool = False) -> List[str]:
        body = list(self)
        return [SOURCE, *body, SINK] if with_markers else body

    def __repr__(self) -> str:
        return f"{self.name}: [{', '.join(self)}]"


class DTree:
    """Single-rooted directed tree with dual projections Q1 and Q2."""

    def __init__(self, tree_id: str = "P1") -> None:
        self.tree_id = tree_id
        self._parent: Dict[str, str] = {}  # child -> parent (root -> SOURCE)
        self._children: Dict[str, List[str]] = {}  # parent -> children, insertion order
        self._q1 = DList(f"{tree_id}.Q1")
        self._q2 = DList(f"{tree_id}.Q2")
        self.edge_log: List[str] = []
        self._reshapes = 0  # counts deletions and moves; insertions keep the order of existing nodes

    # -- construction ------------------------------------------------------
    @classmethod
    def from_file(cls, path: str, tree_id: Optional[str] = None) -> "DTree":
        """Read the ``parent: child1; child2`` format used by the .csx examples."""
        import os

        tree = cls(tree_id or os.path.splitext(os.path.basename(path))[0])
        with open(path, encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith(("#", "--", "**")):
                    continue
                if line.startswith("@@"):
                    break
                parent, _, rest = line.partition(":")
                for child in (c.strip() for c in rest.split(";")):
                    if child:
                        tree.insert(parent.strip(), child)
        return tree

    def insert(self, parent: str, child: str) -> None:
        """Add the edge parent -> child.

        The first call makes ``parent`` the root. Afterwards ``parent`` must
        already exist and ``child`` must not.
        """
        if parent in (SOURCE, SINK) or child in (SOURCE, SINK):
            raise ValueError("SOURCE/SINK markers cannot be tree nodes")
        if not self._parent:
            self._attach(SOURCE, parent)
        elif parent not in self._parent:
            raise KeyError(f"parent {parent!r} is not in the tree")
        if child in self._parent:
            raise ValueError(f"child {child!r} is already in the tree")
        self._attach(parent, child)
        self.edge_log.append(f"({parent}, {child})")

    def _attach(self, parent: str, child: str) -> None:
        end = self._subtree_end_q1(parent)
        self._q2.insert_after(child, parent)
        self._q1.insert_before(child, end)
        self._parent[child] = parent
        self._children.setdefault(parent, []).append(child)

    def _subtree_end_q1(self, u: str) -> str:
        """First node after u in Q1 that u cannot reach (may be SINK)."""
        return self._q1.next(self._subtree_last(u, self._q1))

    def _subtree_last(self, u: str, q: DList) -> str:
        """Last node of u's subtree in projection q, found in O(depth).

        Q1 lists children in insertion order, so its last node is reached by
        following last children; Q2 reverses siblings, so by following first
        children.
        """
        pick = -1 if q is self._q1 else 0
        w = u
        while w in self._children:
            w = self._children[w][pick]
        return w

    # -- structural reconfiguration ---------------------------------------
    def delete(self, node: str) -> None:
        """Remove ``node``; its children are re-attached to its parent.

        Deleting the root is disallowed.
        """
        self._require(node)
        if self.is_root(node):
            raise ValueError("the root cannot be deleted")
        parent = self._parent.pop(node)
        kids = self._children.pop(node, [])
        siblings = self._children[parent]
        i = siblings.index(node)
        siblings[i : i + 1] = kids
        for k in kids:
            self._parent[k] = parent
        if not siblings:
            del self._children[parent]
        self._q1.remove(node)
        self._q2.remove(node)
        self._reshapes += 1

    def delete_subtree(self, node: str) -> List[str]:
        """Remove ``node`` together with all its descendants.

        Returns the removed nodes in Q1 order. Deleting the root's subtree
        (the whole tree) is disallowed, as for delete.
        """
        self._require(node)
        if self.is_root(node):
            raise ValueError("the root cannot be deleted")
        last1 = self._subtree_last(node, self._q1)
        last2 = self._subtree_last(node, self._q2)
        removed = self._q1.cut_block(node, last1)
        self._q2.cut_block(node, last2)
        parent = self._parent[node]
        self._children[parent].remove(node)
        if not self._children[parent]:
            del self._children[parent]
        for v in removed:
            del self._parent[v]
            self._children.pop(v, None)
        self._reshapes += 1
        return removed

    def cut_n_paste(self, subtree_root: str, new_parent: str) -> None:
        """Detach the subtree rooted at ``subtree_root`` and attach it under ``new_parent``.

        The subtree keeps its internal shape and becomes the last child of
        ``new_parent``. ``new_parent`` must not lie inside the moved subtree,
        and the root cannot be moved.
        """
        self._require(subtree_root)
        self._require(new_parent)
        if self.is_root(subtree_root):
            raise ValueError("the root cannot be moved")
        if new_parent == subtree_root or self.can_reach(subtree_root, new_parent):
            raise ValueError("new_parent lies inside the subtree being moved")
        u = subtree_root
        last1 = self._subtree_last(u, self._q1)
        last2 = self._subtree_last(u, self._q2)
        block1 = self._q1.cut_block(u, last1)
        block2 = self._q2.cut_block(u, last2)
        old = self._parent[u]
        self._children[old].remove(u)
        if not self._children[old]:
            del self._children[old]
        # Same placement rule as insert: Q2 right after the parent,
        # Q1 right after the current last node of the parent's subtree.
        last = self._subtree_last(new_parent, self._q1)
        self._q2.paste_block_after(block2, new_parent)
        self._q1.paste_block_after(block1, last)
        self._parent[u] = new_parent
        self._reshapes += 1
        self._children.setdefault(new_parent, []).append(u)

    # -- accessors --------------------------------------------------------
    @property
    def root(self) -> Optional[str]:
        kids = self._children.get(SOURCE)
        return kids[0] if kids else None

    @property
    def source(self) -> str:
        return SOURCE

    @property
    def sink(self) -> str:
        return SINK

    @property
    def Q1(self) -> DList:
        """The Q1 projection itself, for list-level checks (is_left_of, index, ...).

        Live view: read it, but change the tree only through DTree methods.
        """
        return self._q1

    @property
    def Q2(self) -> DList:
        """The Q2 projection itself, for list-level checks. Live view, as Q1."""
        return self._q2

    @property
    def q1(self) -> List[str]:
        """Q1 as a plain list of node names (a copy, without the markers)."""
        return self._q1.to_list()

    @property
    def q2(self) -> List[str]:
        return self._q2.to_list()

    @property
    def size(self) -> int:
        return len(self._parent)

    @property
    def nodes(self) -> List[str]:
        return self.q1

    def __len__(self) -> int:
        return self.size

    def __contains__(self, node: str) -> bool:
        return self.contains(node)

    def __repr__(self) -> str:
        return f"DTree({self.tree_id!r}, size={self.size})\n  {self._q1!r}\n  {self._q2!r}"

    # -- queries ----------------------------------------------------------
    def contains(self, node: str) -> bool:
        return node in self._parent

    def get_parent(self, node: str) -> Optional[str]:
        """Parent of ``node``; ``None`` for the root. Raises KeyError if absent."""
        self._require(node)
        p = self._parent[node]
        return None if p == SOURCE else p

    def children(self, node: str) -> List[str]:
        self._require(node)
        return list(self._children.get(node, []))

    def can_reach(self, u: str, v: str) -> bool:
        """True if there is a directed path of length >= 1 from u to v.

        Irreflexive: can_reach(u, u) is False.
        """
        if u not in self._q1 or v not in self._q1:
            return False
        return self._q1.precedes(u, v) and self._q2.precedes(u, v)

    def can_not_reach(self, u: str, v: str) -> bool:
        return not self.can_reach(u, v)

    def is_root(self, node: str) -> bool:
        return node == self.root

    def is_leaf(self, node: str) -> bool:
        self._require(node)
        return node not in self._children

    def is_ancestor(self, u: str, v: str) -> bool:
        """True if u is a proper ancestor of v (u lies above v on v's root path)."""
        return self.contains(u) and self.contains(v) and self.can_reach(u, v)

    def is_descendant(self, u: str, v: str) -> bool:
        """True if u lies below v. Equivalent to is_ancestor(v, u)."""
        return self.is_ancestor(v, u)

    def same_subtree(self, u: str, v: str) -> bool:
        """True if both nodes are in this tree (and so share its root)."""
        return self.contains(u) and self.contains(v)

    def subtree(self, node: str) -> List[str]:
        """Nodes of the subtree rooted at ``node``, in Q1 order."""
        self._require(node)
        out, v = [node], self._q1.next(node)
        while v != SINK and self.can_reach(node, v):
            out.append(v)
            v = self._q1.next(v)
        return out

    def subtree_size(self, node: str) -> int:
        return len(self.subtree(node))

    def path_to_root(self, node: str) -> List[str]:
        """[node, parent, ..., root]."""
        self._require(node)
        out, v = [], node
        while v != SOURCE:
            out.append(v)
            v = self._parent[v]
        return out

    def root_to_path(self, node: str) -> List[str]:
        """[root, ..., parent, node]."""
        return self.path_to_root(node)[::-1]

    def path(self, u: str, v: str) -> List[str]:
        """Nodes from u down to v, both included; [u] when u == v.

        Raises if u != v and u cannot reach v.
        """
        if u != v and not self.can_reach(u, v):
            raise ValueError(f"{u!r} cannot reach {v!r}")
        out, w = [v], v
        while w != u:
            w = self._parent[w]
            out.append(w)
        return out[::-1]

    def depth(self, node: str) -> int:
        """Distance from the root; the root has depth 0."""
        return len(self.path_to_root(node)) - 1

    # -- helpers ----------------------------------------------------------
    # -- set queries ------------------------------------------------------
    def vmin(self, nodes: Iterable[str] = ()) -> "VMin":
        """Constructed node VMin: the minimum of each index over the nodes (see VMin)."""
        return VMin(self, nodes)

    def vmax(self, nodes: Iterable[str] = ()) -> "VMax":
        """Constructed node VMax: the maximum of each index over the nodes (see VMax)."""
        return VMax(self, nodes)

    def umin(self, nodes: Iterable[str] = ()) -> "UMin":
        """Constructed node UMin: the minimum of each index over the nodes (see UMin)."""
        return UMin(self, nodes)

    def umax(self, nodes: Iterable[str] = ()) -> "UMax":
        """Constructed node UMax: the maximum of each index over the nodes (see UMax)."""
        return UMax(self, nodes)

    def _require(self, node: str) -> None:
        if node not in self._parent:
            raise KeyError(f"node {node!r} is not in the tree")


class _VNode:
    """A constructed node for a set S of tree nodes (E. Olgac, "Topology and Structure of
    Directed Graphs - Inducing a Subgraph", 2021): the minimum (VMin, UMin) or maximum
    (VMax, UMax) of each index over S. V means S takes the target role, can_reach(u, S),
    and U the source role, can_reach(S, v); UMin and VMin hold the same numbers.

    It stores no positions, only the members and, for each of Q1 and Q2, the member holding
    the minimal (or maximal) index there; the two may be different nodes, so the constructed
    node usually corresponds to no real node. Insertions and renumbering keep the order of
    existing nodes, so it stays valid while the tree grows. After a deletion or a cut_n_paste it is
    recomputed from the remaining members on its next use.
    """

    _lowest = True  # VMin keeps the leftmost member, VMax the rightmost

    def __init__(self, tree: "DTree", nodes: Iterable[str] = ()) -> None:
        self._t = tree
        self._members: List[str] = []    # in Q1 order
        self._seen: set = set()
        self._c1: Optional[str] = None
        self._c2: Optional[str] = None
        self._reshapes = tree._reshapes
        for v in nodes:
            self.add(v)

    def _better(self, q: DList, v: str, c: Optional[str]) -> bool:
        if c is None:
            return True
        return q.precedes(v, c) if self._lowest else q.precedes(c, v)

    def add(self, node: str) -> "_VNode":
        """Add a node of the tree to the set; returns the constructed node itself."""
        self._t._require(node)
        if node in self._seen:
            return self
        self._check()
        self._seen.add(node)
        q1 = self._t._q1
        lo, hi = 0, len(self._members)       # keep members sorted by Q1 order
        while lo < hi:
            mid = (lo + hi) // 2
            if q1.precedes(node, self._members[mid]):
                hi = mid
            else:
                lo = mid + 1
        self._members.insert(lo, node)
        if self._better(self._t._q1, node, self._c1):
            self._c1 = node
        if self._better(self._t._q2, node, self._c2):
            self._c2 = node
        self._added(node)
        return self

    def _added(self, node: str) -> None:
        """Hook for subclasses that keep more than the index nodes."""

    def _rebuilt(self) -> None:
        """Hook for subclasses that keep more than the index nodes."""

    def refresh(self) -> None:
        """Drop deleted members and recompute the index nodes."""
        t = self._t
        q1 = t._q1
        self._members = sorted((v for v in self._members if t.contains(v)),
                               key=lambda v: q1.index(v))
        self._seen = set(self._members)
        self._c1 = self._c2 = None
        for v in self._members:
            if self._better(t._q1, v, self._c1):
                self._c1 = v
            if self._better(t._q2, v, self._c2):
                self._c2 = v
        self._reshapes = t._reshapes
        self._rebuilt()

    def _check(self) -> None:
        t = self._t
        if self._reshapes != t._reshapes:
            self.refresh()

    @property
    def members(self) -> List[str]:
        self._check()
        return list(self._members)

    @property
    def index_nodes(self) -> tuple:
        """The members holding the minimal (VMin, UMin) or maximal (VMax, UMax) index in Q1 and in Q2 (possibly two different nodes)."""
        self._check()
        return self._c1, self._c2

    def __len__(self) -> int:
        self._check()
        return len(self._members)


class VMin(_VNode):
    """S in the target role, can_reach(u, S). Minimum of each index over a node set: u reaches all of the set exactly when u lies
    strictly left of VMin in both Q1 and Q2."""

    _lowest = True

    def reaches_all(self, u: str) -> bool:
        """True if u reaches every node of the set (vacuously True for an empty set)."""
        self._check()
        t = self._t
        if not t.contains(u):
            return False
        if self._c1 is None:
            return True
        return t._q1.precedes(u, self._c1) and t._q2.precedes(u, self._c2)


class VMax(_VNode):
    """S in the target role, can_reach(u, S). Maximum of each index over a node set: lying
    strictly left of VMax in both Q1 and Q2 is necessary for u to reach some of the set, but
    not sufficient, so may_reach_some is only a filter; reaches_some is exact."""

    _lowest = False

    def may_reach_some(self, u: str) -> bool:
        """Fast rejection: False means u reaches no node of the set. True is not a confirmation."""
        self._check()
        t = self._t
        if self._c1 is None or not t.contains(u):
            return False
        return t._q1.precedes(u, self._c1) and t._q2.precedes(u, self._c2)

    def reaches_some(self, u: str) -> bool:
        """True if u reaches at least one node of the set (exact).

        The subtree of u is the block directly after u in Q1, so u reaches some member
        exactly when the first member after u in Q1 lies in it: a binary search over the
        members (kept in Q1 order) and one reachability test.
        """
        if not self.may_reach_some(u):
            return False
        t, m = self._t, self._members
        q1 = t._q1
        lo, hi = 0, len(m)
        while lo < hi:
            mid = (lo + hi) // 2
            if q1.precedes(u, m[mid]):
                hi = mid
            else:
                lo = mid + 1
        return lo < len(m) and t.can_reach(u, m[lo])


class UMax(_VNode):
    """S in the source role, can_reach(S, v). Maximum of each index over a node set: v is
    reached by all of the set exactly when v lies strictly right of UMax in both Q1 and Q2."""

    _lowest = False

    def reached_by_all(self, v: str) -> bool:
        """True if every node of the set reaches v (vacuously True for an empty set)."""
        self._check()
        t = self._t
        if not t.contains(v):
            return False
        if self._c1 is None:
            return True
        return t._q1.precedes(self._c1, v) and t._q2.precedes(self._c2, v)


class UMin(_VNode):
    """S in the source role, can_reach(S, v). Minimum of each index over a node set: lying
    strictly right of UMin in both Q1 and Q2 is necessary for v to be reached by some of the
    set, but not sufficient, so may_be_reached_by_some is only a filter; reached_by_some is
    exact.

    The exact test keeps the topmost members (those with no ancestor in the set) in Q1
    order. Their subtrees are disjoint, so if one of them is an ancestor of v, no other
    topmost member lies between it and v in Q1: the last topmost member before v in Q1 is
    the only one to test.
    """

    _lowest = True

    def __init__(self, tree: "DTree", nodes: Iterable[str] = ()) -> None:
        self._tops: List[str] = []       # topmost members, in Q1 order
        super().__init__(tree, nodes)

    def _last_top_before(self, v: str) -> int:
        """Number of topmost members strictly left of v in Q1."""
        q1, m = self._t._q1, self._tops
        lo, hi = 0, len(m)
        while lo < hi:
            mid = (lo + hi) // 2
            if q1.precedes(m[mid], v):
                lo = mid + 1
            else:
                hi = mid
        return lo

    def _covered(self, v: str) -> bool:
        i = self._last_top_before(v)
        return i > 0 and self._t.can_reach(self._tops[i - 1], v)

    def _added(self, node: str) -> None:
        if self._covered(node):
            return                       # an ancestor of node is already in the set
        i = self._last_top_before(node)
        t, m = self._t, self._tops
        while i < len(m) and t.can_reach(node, m[i]):
            del m[i]                     # node is above them: they are no longer topmost
        m.insert(i, node)

    def _rebuilt(self) -> None:
        self._tops = []
        t = self._t
        for v in self._members:          # Q1 order: ancestors come first
            if not (self._tops and t.can_reach(self._tops[-1], v)):
                self._tops.append(v)

    def may_be_reached_by_some(self, v: str) -> bool:
        """Fast rejection: False means no node of the set reaches v; True is not a confirmation."""
        self._check()
        t = self._t
        if self._c1 is None or not t.contains(v):
            return False
        return t._q1.precedes(self._c1, v) and t._q2.precedes(self._c2, v)

    def reached_by_some(self, v: str) -> bool:
        """True if at least one node of the set reaches v (exact, O(log k))."""
        if not self.may_be_reached_by_some(v):
            return False
        return self._covered(v)
