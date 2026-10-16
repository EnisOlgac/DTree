namespace DirectedTrees {

    /// <summary>
    /// Single-rooted directed tree encoded by two linear projections Q1 and Q2.
    /// </summary>
    /// <remarks>
    /// Q1 is the pre-order with children left to right (insertion order); Q2 the pre-order
    /// with siblings right to left. Node u reaches node v if and only if u strictly precedes v
    /// in both Q1 and Q2 (irreflexive: no node reaches itself). A new child is the last child of
    /// its parent in Q1 and the first in Q2, so every change is local to both lists.
    /// Design and API: Enis Olgac. This C# version mirrors the Python reference implementation
    /// (1.1.0), which was written with Claude (Anthropic).
    /// </remarks>
    public sealed class DTree {
        private readonly Dictionary<string, string> _parent = new();               // child -> parent (root -> SOURCE)
        private readonly Dictionary<string, List<string>> _children = new();       // parent -> children, insertion order
        private readonly DList _q1;
        private readonly DList _q2;
        private readonly List<string> _edgeLog = new();

        public DTree(string treeId = "P1") {
            TreeId = treeId;
            _q1 = new DList(treeId + ".Q1");
            _q2 = new DList(treeId + ".Q2");
        }

        public string TreeId { get; }

        // -- construction -----------------------------------------------------------

        /// <summary>Read the "parent: child1; child2" format used by the .csx examples.</summary>
        public static DTree FromFile(string path, string? treeId = null) {
            var tree = new DTree(treeId ?? System.IO.Path.GetFileNameWithoutExtension(path));
            foreach (var raw in File.ReadLines(path)) {
                var line = raw.Trim().TrimStart('﻿');
                if (line.Length == 0 || line.StartsWith('#') || line.StartsWith("--") || line.StartsWith("**")) continue;
                if (line.StartsWith("@@")) break;
                int colon = line.IndexOf(':');
                if (colon < 0) continue;
                var parent = line[..colon].Trim();
                foreach (var part in line[(colon + 1)..].Split(';')) {
                    var child = part.Trim();
                    if (child.Length > 0) tree.Insert(parent, child);
                }
            }
            return tree;
        }

        /// <summary>
        /// Add the edge parent -> child. The first call makes parent the root; afterwards parent
        /// must already exist and child must not.
        /// </summary>
        public void Insert(string parent, string child) {
            if (IsMarker(parent) || IsMarker(child))
                throw new ArgumentException("SOURCE/SINK markers cannot be tree nodes");
            if (_parent.Count == 0)
                Attach(Marker.Source, parent);
            else if (!_parent.ContainsKey(parent))
                throw new KeyNotFoundException($"parent '{parent}' is not in the tree");
            if (_parent.ContainsKey(child))
                throw new ArgumentException($"child '{child}' is already in the tree");
            Attach(parent, child);
            _edgeLog.Add($"({parent}, {child})");
        }

        private static bool IsMarker(string v) => v == Marker.Source || v == Marker.Sink;

        private void Attach(string parent, string child) {
            var end = SubtreeEndQ1(parent);
            _q2.InsertAfter(child, parent);
            _q1.InsertBefore(child, end);
            _parent[child] = parent;
            ChildList(parent).Add(child);
        }

        private List<string> ChildList(string parent) {
            if (!_children.TryGetValue(parent, out var list)) {
                list = new List<string>();
                _children[parent] = list;
            }
            return list;
        }

        /// <summary>First node after u in Q1 that u cannot reach (may be SINK).</summary>
        private string SubtreeEndQ1(string u) => _q1.Next(SubtreeLast(u, _q1))!;

        /// <summary>
        /// Last node of u's subtree in projection q, in O(depth): Q1 lists children in insertion
        /// order (follow last children), Q2 reverses siblings (follow first children).
        /// </summary>
        private string SubtreeLast(string u, DList q) {
            bool last = ReferenceEquals(q, _q1);
            var w = u;
            while (_children.TryGetValue(w, out var kids)) w = last ? kids[^1] : kids[0];
            return w;
        }

        // -- structural reconfiguration -------------------------------------------

        /// <summary>Remove node; its children are re-attached to its parent, in its place. The root cannot be deleted.</summary>
        public void Delete(string node) {
            Require(node);
            if (IsRoot(node)) throw new InvalidOperationException("the root cannot be deleted");
            var parent = _parent[node];
            _parent.Remove(node);
            var kids = _children.TryGetValue(node, out var k) ? k : new List<string>();
            _children.Remove(node);
            var siblings = _children[parent];
            int i = siblings.IndexOf(node);
            siblings.RemoveAt(i);
            siblings.InsertRange(i, kids);
            foreach (var c in kids) _parent[c] = parent;
            if (siblings.Count == 0) _children.Remove(parent);
            _q1.Remove(node);
            _q2.Remove(node);
        }

        /// <summary>Remove node together with all its descendants; returns them in Q1 order.</summary>
        public List<string> DeleteSubtree(string node) {
            Require(node);
            if (IsRoot(node)) throw new InvalidOperationException("the root cannot be deleted");
            var last1 = SubtreeLast(node, _q1);
            var last2 = SubtreeLast(node, _q2);
            var removed = _q1.CutBlock(node, last1);
            _q2.CutBlock(node, last2);
            var parent = _parent[node];
            _children[parent].Remove(node);
            if (_children[parent].Count == 0) _children.Remove(parent);
            foreach (var v in removed) {
                _parent.Remove(v);
                _children.Remove(v);
            }
            return removed;
        }

        /// <summary>
        /// Detach the subtree rooted at subtreeRoot and attach it as the last child of newParent.
        /// newParent must not lie inside the moved subtree; the root cannot be moved.
        /// </summary>
        public void CutNPaste(string subtreeRoot, string newParent) {
            Require(subtreeRoot);
            Require(newParent);
            if (IsRoot(subtreeRoot)) throw new InvalidOperationException("the root cannot be moved");
            if (newParent == subtreeRoot || CanReach(subtreeRoot, newParent))
                throw new InvalidOperationException("newParent lies inside the subtree being moved");
            var u = subtreeRoot;
            var last1 = SubtreeLast(u, _q1);
            var last2 = SubtreeLast(u, _q2);
            var block1 = _q1.CutBlock(u, last1);
            var block2 = _q2.CutBlock(u, last2);
            var old = _parent[u];
            _children[old].Remove(u);
            if (_children[old].Count == 0) _children.Remove(old);
            // Same placement rule as Insert: Q2 right after the parent,
            // Q1 right after the current last node of the parent's subtree.
            var last = SubtreeLast(newParent, _q1);
            _q2.PasteBlockAfter(block2, newParent);
            _q1.PasteBlockAfter(block1, last);
            _parent[u] = newParent;
            ChildList(newParent).Add(u);
        }

        // -- accessors -------------------------------------------------------------

        public string? Root => _children.TryGetValue(Marker.Source, out var kids) && kids.Count > 0 ? kids[0] : null;
        public string Source => Marker.Source;
        public string Sink => Marker.Sink;

        /// <summary>The Q1 projection itself, for list-level checks. Read it; change the tree only through DTree.</summary>
        public DList Q1 => _q1;

        /// <summary>The Q2 projection itself, for list-level checks. Read it; change the tree only through DTree.</summary>
        public DList Q2 => _q2;

        public int Size => _parent.Count;
        public List<string> Nodes => _q1.ToList();
        public string EdgeLog => string.Join("\n", _edgeLog);

        public override string ToString() => $"DTree('{TreeId}', size={Size})\n  {_q1}\n  {_q2}";

        // -- queries ---------------------------------------------------------------

        public bool Contains(string node) => _parent.ContainsKey(node);

        /// <summary>Parent of node; null for the root. Throws if node is absent.</summary>
        public string? GetParent(string node) {
            Require(node);
            var p = _parent[node];
            return p == Marker.Source ? null : p;
        }

        public List<string> Children(string node) {
            Require(node);
            return _children.TryGetValue(node, out var kids) ? new List<string>(kids) : new List<string>();
        }

        /// <summary>True if there is a directed path of length at least 1 from u to v (irreflexive).</summary>
        public bool CanReach(string u, string v) =>
            _q1.Contains(u) && _q1.Contains(v) && _q1.Precedes(u, v) && _q2.Precedes(u, v);

        public bool CanNotReach(string u, string v) => !CanReach(u, v);

        public bool IsRoot(string node) => node == Root;

        public bool IsLeaf(string node) {
            Require(node);
            return !_children.ContainsKey(node);
        }

        /// <summary>True if u is a proper ancestor of v.</summary>
        public bool IsAncestor(string u, string v) => Contains(u) && Contains(v) && CanReach(u, v);

        /// <summary>True if u lies below v. Equivalent to IsAncestor(v, u).</summary>
        public bool IsDescendant(string u, string v) => IsAncestor(v, u);

        /// <summary>True if both nodes are in this tree (and so share its root).</summary>
        public bool SameSubtree(string u, string v) => Contains(u) && Contains(v);

        /// <summary>Nodes of the subtree rooted at node, in Q1 order.</summary>
        public List<string> Subtree(string node) {
            Require(node);
            var result = new List<string> { node };
            for (var v = _q1.Next(node)!; v != Marker.Sink && CanReach(node, v); v = _q1.Next(v)!) result.Add(v);
            return result;
        }

        public int SubtreeSize(string node) => Subtree(node).Count;

        /// <summary>[node, parent, ..., root].</summary>
        public List<string> PathToRoot(string node) {
            Require(node);
            var result = new List<string>();
            for (var v = node; v != Marker.Source; v = _parent[v]) result.Add(v);
            return result;
        }

        /// <summary>[root, ..., parent, node].</summary>
        public List<string> RootToPath(string node) {
            var path = PathToRoot(node);
            path.Reverse();
            return path;
        }

        /// <summary>Nodes from u down to v, both included; [u] when u == v.</summary>
        public List<string> Path(string u, string v) {
            if (u != v && !CanReach(u, v)) throw new InvalidOperationException($"'{u}' cannot reach '{v}'");
            var result = new List<string> { v };
            for (var w = v; w != u;) {
                w = _parent[w];
                result.Add(w);
            }
            result.Reverse();
            return result;
        }

        /// <summary>Distance from the root; the root has depth 0.</summary>
        public int Depth(string node) => PathToRoot(node).Count - 1;

        private void Require(string node) {
            if (!_parent.ContainsKey(node)) throw new KeyNotFoundException($"node '{node}' is not in the tree");
        }
    }
}
