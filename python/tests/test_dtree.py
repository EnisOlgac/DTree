"""Tests for the Python DTree: every query is checked against a brute-force
reference computed from the parent map alone (no projections)."""

import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from dtree import SINK, SOURCE, DTree  # noqa: E402

EXAMPLES = os.path.join(HERE, "..", "..", "examples")


def ref_ancestors(parent, v):
    out = []
    while v in parent:
        out.append(v)
        v = parent[v]
    return out  # [v, ..., child of root]


def ref_preorder(children, root, reverse=False):
    out, stack = [], [root]
    while stack:
        n = stack.pop()
        out.append(n)
        kids = children.get(n, [])
        stack.extend(kids if reverse else reversed(kids))
    return out


class Reference:
    """Plain parent/children model mirroring every operation."""

    def __init__(self):
        self.parent, self.children, self.root = {}, {}, None

    def insert(self, u, v):
        if self.root is None:
            self.root = u
        self.parent[v] = u
        self.children.setdefault(u, []).append(v)

    def delete(self, v):
        p = self.parent.pop(v)
        kids = self.children.pop(v, [])
        sib = self.children[p]
        i = sib.index(v)
        sib[i : i + 1] = kids
        for k in kids:
            self.parent[k] = p
        if not sib:
            del self.children[p]

    def delete_subtree(self, v):
        stack, gone = [v], []
        while stack:
            n = stack.pop()
            gone.append(n)
            stack.extend(self.children.pop(n, []))
        p = self.parent[v]
        self.children[p].remove(v)
        if not self.children[p]:
            del self.children[p]
        for n in gone:
            del self.parent[n]

    def move(self, u, p):
        old = self.parent[u]
        self.children[old].remove(u)
        if not self.children[old]:
            del self.children[old]
        self.parent[u] = p
        self.children.setdefault(p, []).append(u)

    def nodes(self):
        return [self.root] + list(self.parent)


def labels_strictly_increase(q):
    prev, cell = q.first, q.first.next
    while cell is not None:
        if not q._lt(prev, cell):
            return False
        prev, cell = cell, cell.next
    return True


def check(tc, t, ref):
    tc.assertTrue(labels_strictly_increase(t._q1))
    tc.assertTrue(labels_strictly_increase(t._q2))
    nodes = ref.nodes()
    tc.assertEqual(t.size, len(nodes))
    tc.assertEqual(t.root, ref.root)
    tc.assertEqual(t.q1, ref_preorder(ref.children, ref.root))
    tc.assertEqual(t.q2, ref_preorder(ref.children, ref.root, reverse=True))
    par = dict(ref.parent)
    for v in nodes:
        anc = ref_ancestors(par, v) + [ref.root]  # root has no parent entry
        tc.assertEqual(t.path_to_root(v), anc)
        tc.assertEqual(t.root_to_path(v), anc[::-1])
        tc.assertEqual(t.depth(v), len(anc) - 1)
        tc.assertEqual(t.get_parent(v), par.get(v))
        tc.assertEqual(t.is_leaf(v), v not in ref.children)
    sample = nodes if len(nodes) <= 40 else random.sample(nodes, 40)
    for u in sample:
        for v in sample:
            anc_v = t.path_to_root(v)
            tc.assertEqual(t.can_reach(u, v), u in anc_v and u != v, (u, v))
            tc.assertEqual(t.is_ancestor(u, v), u in anc_v and u != v)
            tc.assertEqual(t.is_descendant(v, u), u in anc_v and u != v)


def random_tree(n, seed):
    rnd = random.Random(seed)
    t, ref = DTree("R"), Reference()
    names = ["n0"]
    for i in range(1, n):
        p = rnd.choice(names)
        t.insert(p, f"n{i}")
        ref.insert(p, f"n{i}")
        names.append(f"n{i}")
    return t, ref, rnd


class TestDocumentedExamples(unittest.TestCase):
    def test_readme_usage(self):
        t = DTree("P1")
        t.insert("A", "B")
        t.insert("B", "C")
        self.assertTrue(t.can_reach("A", "C"))
        self.assertEqual(t.path_to_root("C"), ["C", "B", "A"])
        self.assertEqual(t.root_to_path("C"), ["A", "B", "C"])
        self.assertEqual(t.root, "A")
        self.assertIsNone(t.get_parent("A"))
        self.assertEqual(t.depth("A"), 0)
        self.assertEqual(t.source, SOURCE)
        self.assertEqual(t.sink, SINK)

    def test_no_self_reachability(self):
        t = DTree()
        t.insert("A", "B")
        for v in ("A", "B"):
            self.assertFalse(t.can_reach(v, v))
            self.assertTrue(t.can_not_reach(v, v))
            self.assertFalse(t.is_ancestor(v, v))
        self.assertEqual(t.subtree("A"), ["A", "B"])
        self.assertEqual(t.path("A", "A"), ["A"])
        with self.assertRaises(ValueError):
            t.cut_n_paste("B", "B")

    def test_list_level_access(self):
        t = DTree()
        t.insert("A", "B")
        t.insert("A", "C")  # B and C are not connected
        self.assertTrue(t.Q1.is_left_of("B", "C"))
        self.assertTrue(t.Q2.is_left_of("C", "B"))
        self.assertEqual(list(t.Q1), t.q1)

    def test_insert_rules(self):
        t = DTree()
        t.insert("A", "B")
        with self.assertRaises(KeyError):
            t.insert("X", "Y")  # parent must exist
        with self.assertRaises(ValueError):
            t.insert("A", "B")  # child must not exist

    def test_delete_root_disallowed(self):
        t = DTree()
        t.insert("A", "B")
        with self.assertRaises(ValueError):
            t.delete("A")

    def test_two_kinds_of_delete(self):
        def build():
            t = DTree()
            for u, v in [("A", "B"), ("B", "C"), ("B", "D"), ("A", "E")]:
                t.insert(u, v)
            return t
        t = build()
        t.delete("B")  # children move up to A, in B's place
        self.assertEqual(t.children("A"), ["C", "D", "E"])
        self.assertEqual(t.q1, ["A", "C", "D", "E"])
        t = build()
        self.assertEqual(t.delete_subtree("B"), ["B", "C", "D"])
        self.assertEqual(t.q1, ["A", "E"])
        self.assertEqual(t.q2, ["A", "E"])
        with self.assertRaises(ValueError):
            t.delete_subtree("A")

    def test_cut_into_own_subtree_rejected(self):
        t = DTree()
        t.insert("A", "B")
        t.insert("B", "C")
        with self.assertRaises(ValueError):
            t.cut_n_paste("B", "C")

    def test_example_files(self):
        for name in ["Test.csx", "Test1.csx", "test23.csx"]:
            path = os.path.join(EXAMPLES, name)
            if os.path.exists(path):
                t = DTree.from_file(path)
                self.assertEqual(t.root, "01")
                self.assertTrue(t.can_reach("01", "22"))
                self.assertEqual(t.path_to_root("22"), ["22", "10", "06", "04", "01"])


class TestDList(unittest.TestCase):
    def test_list_cs_operations(self):
        from dtree import DList
        q = DList("Q")
        self.assertEqual((q.source, q.sink), (SOURCE, SINK))
        q.insert_before("a", SINK)
        q.insert_after("c", "a")
        q.insert_before("b", "c")
        self.assertEqual(q.to_list(), ["a", "b", "c"])
        self.assertEqual(q.to_list(with_markers=True), [SOURCE, "a", "b", "c", SINK])
        self.assertTrue(q.is_left_of("a", "c") and q.is_right_of("c", "a"))
        self.assertTrue(q.is_self_or_left_of("b", "b") and q.is_self_or_right_of("b", "b"))
        self.assertFalse(q.is_left_of("b", "b"))
        self.assertEqual((q.prev("b"), q.next("b")), ("a", "c"))
        self.assertTrue(q.is_allocated("a") and q.is_not_allocated("z"))
        self.assertIsNone(q.index("z"))
        # edge cases of List.cs
        q.insert_before("d", SOURCE)  # redirected to after SOURCE
        q.insert_after("e", SINK)     # redirected to before SINK
        self.assertEqual(q.to_list(), ["d", "a", "b", "c", "e"])
        q.insert_after("a", "a")      # no-op
        q.insert_after("b", "a")      # already there: no-op
        # re-inserting an existing node moves it
        q.insert_after("d", "c")
        self.assertEqual(q.to_list(), ["a", "b", "c", "d", "e"])
        r = DList("R")
        for n in ["a", "b", "c", "d", "e"]:
            r.insert_before(n, SINK)
        self.assertTrue(q.is_same_as(r))
        r.remove("c")
        self.assertFalse(q.is_same_as(r))


class TestAgainstReference(unittest.TestCase):
    def test_random_inserts(self):
        for seed in range(30):
            t, ref, _ = random_tree(60, seed)
            check(self, t, ref)

    def test_random_deletes_and_moves(self):
        for seed in range(30):
            t, ref, rnd = random_tree(80, seed)
            for _ in range(40):
                nodes = [n for n in ref.nodes() if n != ref.root]
                if len(nodes) < 10:
                    break
                r = rnd.random()
                if r < 0.35:
                    v = rnd.choice(nodes)
                    t.delete(v)
                    ref.delete(v)
                elif r < 0.5:
                    v = rnd.choice(nodes)
                    expected = t.subtree(v)
                    self.assertEqual(t.delete_subtree(v), expected)
                    ref.delete_subtree(v)
                    for n in expected:
                        self.assertFalse(t.contains(n))
                else:
                    u = rnd.choice(nodes)
                    banned = set(t.subtree(u))
                    targets = [n for n in ref.nodes() if n not in banned]
                    p = rnd.choice(targets)
                    t.cut_n_paste(u, p)
                    ref.move(u, p)
                check(self, t, ref)


class TestNoSizeLimit(unittest.TestCase):
    def test_deep_chain(self):
        t = DTree()
        for i in range(5000):
            t.insert(f"v{i}", f"v{i + 1}")
        self.assertEqual(t.depth("v5000"), 5000)
        self.assertTrue(t.can_reach("v0", "v5000"))
        self.assertFalse(t.can_reach("v5000", "v0"))
        # growing a chain only appends at the list ends: no renumbering at all
        self.assertEqual((t.Q1.renumber_count, t.Q2.renumber_count), (0, 0))

    def test_wide_node(self):
        t = DTree()
        for i in range(5000):
            t.insert("r", f"c{i}")
        self.assertEqual(t.subtree_size("r"), 5001)
        self.assertFalse(t.can_reach("c1", "c2"))
        self.assertEqual(t.q2[:3], ["r", "c4999", "c4998"])
        self.assertTrue(labels_strictly_increase(t._q2))

    def test_growth_at_both_ends(self):
        from dtree import DList
        q = DList("Q")
        for i in range(5000):
            q.insert_before(f"r{i}", SINK)   # grow to the right
            q.insert_after(f"l{i}", SOURCE)  # grow to the left
        self.assertTrue(labels_strictly_increase(q))
        self.assertEqual(q.to_list()[:2], ["l4999", "l4998"])
        self.assertEqual(q.to_list()[-2:], ["r4998", "r4999"])

    def test_star_needs_no_renumbering(self):
        t = DTree()
        t.insert("r", "x")
        t.insert("r", "y")
        for i in range(5000):
            t.insert("x", f"c{i}")  # star under an inner node: same gap every time
        self.assertEqual((t.Q1.renumber_count, t.Q2.renumber_count), (0, 0))
        self.assertTrue(t.can_reach("x", "c4999"))
        self.assertFalse(t.can_reach("c0", "c1"))

    def test_alternating_worst_case(self):
        # always insert into the newer half of the last gap, alternating sides:
        # mediant denominators grow like Fibonacci numbers and force renumbering
        t = DTree()
        left = "n0"
        for i in range(1, 4000):
            t.insert(left, f"n{i}")
            if i % 2 == 0:
                left = f"n{i}"
        self.assertGreater(t.Q2.renumber_count, 0)
        self.assertTrue(labels_strictly_increase(t._q1))
        self.assertTrue(labels_strictly_increase(t._q2))
        for q in (t._q1, t._q2):
            self.assertTrue(all(c.den.bit_length() <= 64 for c in q._cells.values() if c.den))

    def test_random_list_operations(self):
        from dtree import DList
        rnd = random.Random(7)
        q, ref = DList("Q"), []
        for i in range(20000):
            r = rnd.random()
            if ref and r < 0.15:
                v = rnd.choice(ref)
                q.remove(v)
                ref.remove(v)
                continue
            name = f"v{i}"
            if not ref or r < 0.25:
                q.insert_after(name, SOURCE)
                ref.insert(0, name)
            else:
                # hammer a few hot spots to force renumbering
                j = rnd.choice([0, len(ref) // 2, len(ref) - 1, rnd.randrange(len(ref))])
                if rnd.random() < 0.5:
                    q.insert_after(name, ref[j])
                    ref.insert(j + 1, name)
                else:
                    q.insert_before(name, ref[j])
                    ref.insert(j, name)
        self.assertEqual(q.to_list(), ref)
        self.assertTrue(labels_strictly_increase(q))

    def test_adversarial_gaps(self):
        # alternate between the two most crowded gaps in Q2 and Q1
        t = DTree()
        t.insert("r", "a")
        for i in range(3000):
            t.insert("r", f"x{i}")
            t.insert("a", f"y{i}")
        self.assertTrue(labels_strictly_increase(t._q1))
        self.assertTrue(labels_strictly_increase(t._q2))
        self.assertTrue(t.can_reach("a", "y2999"))
        self.assertFalse(t.can_reach("x0", "y0"))


if __name__ == "__main__":
    unittest.main()
