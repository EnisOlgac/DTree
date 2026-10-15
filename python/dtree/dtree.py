"""DTree: a single-rooted directed tree encoded by two linear projections.

Python implementation of the DTree design and API by Enis Olgac (C# original in
``src/``). This port was written with Claude (Anthropic) and checked against a
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
  Insertion costs O(depth of the subtree below u) plus O(log n) amortized
  relabeling.
* delete(v): v is removed from both projections; its children move up to v's
  parent and keep their relative order (a cut-and-paste of v's children).
* delete_subtree(v): the contiguous block of v's subtree is removed from both
  projections.
* cut_n_paste(u, p): the contiguous block of u's subtree is lifted out of both
  projections and re-inserted under p using the same rule as insert.

Positions are integer labels maintained with the order-maintenance scheme of
Bender, Cole, Demaine, Farach-Colton and Zito ("Two simplified algorithms for
maintaining order in a list", ESA 2002): when two neighbors have no free label
between them, only the smallest surrounding label range that is sparse enough
is spread out again. This costs O(log n) amortized per insertion and imposes no
depth or width limit.
"""

from __future__ import annotations

from typing import Dict, Iterator, List, Optional

SOURCE = "["
SINK = "]"

_BITS = 128  # initial label universe [0, 2**_BITS); doubled when it fills up
_T = 1.5  # density parameter of the order-maintenance scheme (1 < T < 2)
_STEP = 1 << 64  # initial gap: label step used when appending at either end of a list


class _Cell:
    __slots__ = ("name", "prev", "next", "label")

    def __init__(self, name: str) -> None:
        self.name = name
        self.prev: Optional[_Cell] = None
        self.next: Optional[_Cell] = None
        self.label = 0


class DList:
    """Doubly linked list with order labels (O(1) precedence test)."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._cells: Dict[str, _Cell] = {}
        self.first = self._new(SOURCE)
        self.last = self._new(SINK)
        self.first.next = self.last
        self.last.prev = self.first
        self._bits = _BITS
        self.first.label = 0
        self.last.label = (1 << self._bits) - 1

    # -- internals --------------------------------------------------------
    def _new(self, name: str) -> _Cell:
        cell = _Cell(name)
        self._cells[name] = cell
        return cell

    @staticmethod
    def _spread(lo: _Cell, count: int, start: int, size: int) -> None:
        """Give count consecutive cells from lo evenly spaced labels in [start, start+size)."""
        cell = lo
        for j in range(count):
            cell.label = start + (size * j) // count
            cell = cell.next

    def _rebalance(self, cell: _Cell) -> None:
        """Spread the smallest aligned label range around cell that is sparse enough."""
        lo = hi = cell
        count, base = 1, cell.label
        for i in range(1, self._bits + 1):
            size = 1 << i
            start = base & ~(size - 1)
            while lo.prev is not None and lo.prev.label >= start:
                lo = lo.prev
                count += 1
            while hi.next is not None and hi.next.label < start + size:
                hi = hi.next
                count += 1
            if count * _T ** i <= size:
                self._spread(lo, count, start, size)
                return
        # Whole universe too dense: double the number of label bits.
        self._bits *= 2
        n = len(self._cells)
        self._spread(self.first, n, 0, 1 << self._bits)
        self.last.label = (1 << self._bits) - 1

    def _link_after(self, cell: _Cell, prev: _Cell) -> None:
        nxt = prev.next
        cell.prev, cell.next = prev, nxt
        prev.next = cell
        nxt.prev = cell
        gap = nxt.label - prev.label
        if gap >= 2:
            # Appending at either end takes a fixed step instead of the midpoint,
            # so growing a list at its ends almost never needs renumbering.
            # The first node goes to the middle of the range, so the list can grow
            # equally far to the right (larger labels) and to the left (smaller
            # labels). This is the signed-position idea (positives to the right,
            # negatives to the left) with the range shifted to start at 0.
            if prev is self.first and nxt is self.last:
                cell.label = (prev.label + nxt.label) // 2
            elif nxt is self.last:
                cell.label = prev.label + min(gap // 2, _STEP)
            elif prev is self.first:
                cell.label = nxt.label - min(gap // 2, _STEP)
            else:
                cell.label = (prev.label + nxt.label) // 2
        else:
            cell.label = prev.label  # temporary duplicate, resolved by rebalancing
            self._rebalance(cell)

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

    def label(self, name: str) -> int:
        return self._cells[name].label

    def index(self, name: str) -> Optional[int]:
        """Position label of ``name``, or None if it is not in the list (List.cs: Index)."""
        cell = self._cells.get(name)
        return cell.label if cell else None

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
        return self._cells[v].label < self._cells[u].label

    def is_self_or_left_of(self, v: str, u: str) -> bool:
        return self._cells[v].label <= self._cells[u].label

    def is_right_of(self, v: str, u: str) -> bool:
        return self._cells[v].label > self._cells[u].label

    def is_self_or_right_of(self, v: str, u: str) -> bool:
        return self._cells[v].label >= self._cells[u].label

    def precedes(self, u: str, v: str) -> bool:
        """Strict order: u lies left of v (same as is_left_of)."""
        return self._cells[u].label < self._cells[v].label

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
    def _require(self, node: str) -> None:
        if node not in self._parent:
            raise KeyError(f"node {node!r} is not in the tree")
