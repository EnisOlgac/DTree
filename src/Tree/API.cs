namespace DirectedTrees {
    public partial class DTree {
        // -- Constructor --

        /// <summary>
        /// Initializes a new directed tree with the given identifier.
        /// The root is determined implicitly as the source of the first inserted edge.
        /// </summary>
        public static DTree CreateDTree(string id = "P1") => new DTree(id);

        // -- Metadata --

        /// <summary>
        /// Return the ID of the root node, or null if empty.
        /// </summary>
        public string Root => _Q1.First;

        /// <summary>
        /// Return the identifier of this tree.
        /// </summary>
        public string TreeId => _Def;

        /// <summary>
        /// Return the number of nodes in the tree.
        /// </summary>
        public int Size => _Vs.Count;

        /// <summary>
        /// Return a list of all node IDs in the tree.
        /// </summary>
        public List<string> Nodes => _Vs.Keys.ToList();

        /// <summary>
        /// Get a formatted log of all edge insertions in the tree.
        /// Useful for debugging or audit trails.
        /// </summary>
        public string EdgeLog => _EdgeLog;

        /// <summary>
        /// Returns the Source node: the unique node with no predecessor.
        /// Acts as the start delimiter of Q1 and Q2 projections.
        /// </summary>
        public string Source => _Source;

        /// <summary>
        /// Returns the Sink node: the unique node with no children.
        /// Acts as the end delimiter of Q1 and Q2 projections.
        /// </summary>
        public string Sink => _Sink;

        // -- Projections as string (optional) --

        /// <summary>
        /// Return Q1 projection as a list of nodes.
        /// <summary>
        public List<string> Q1 => _Q1.ConvertToString();

        /// <summary>
        /// Return Q2 projection as a list of nodes.
        /// </summary>
        public List<string> Q2 => _Q2.ConvertToString();

        /// <summary>
        /// Return Q1 projection as a string.
        /// <summary>
        public string PrintQ1 => _Q1.ToString();

        /// <summary>
        /// Return Q2 projection as a string.
        /// </summary>
        public string PrintQ2 => _Q2.ToString();

        // -- Structural Reconfiguration --

        // -- Insertion --

        /// <summary>
        /// Adds a directed edge from parent to child.
        /// The parent must already exist; the child must not.
        /// Updates Q1 and Q2 projections accordingly.
        /// </summary>
        public void InsEdge(string u, string v) => _InsEdge(u, v);

        /// <summary>
        /// Detach a subtree from its root and attach it to another.
        /// </summary>
        public void CutNPaste(string u1, string u2) { }

        /// <summary>
        /// Remove a node and reattach its children, if any, to its parent.
        /// If node is the root, the operation is disallowed.
        /// </summary>
        public void Delete(string node) { }

        // -- Queries --

        /// <summary>
        /// Check if node u can reach node v.
        /// </summary>
        public bool CanReach(string u, string v) => _CanReach(u, v);

        /// <summary>
        /// Check if node u cannot reach node v.
        /// </summary>
        public bool CanNotReach(string u, string v) => _CanNotReach(u, v);

        // Ancestry and Structure

        /// <summary>
        /// Returns true if the given node is the root of the tree.
        /// </summary>
        public bool IsRoot(string node) => node == _Q1.First;

        /// <summary>
        /// Returns subtree rooted at the given node.
        /// </summary>
        public List<string> Subtree(string node) => _Subtree(node);

        /// <summary>
        /// Returns u the parent of v.
        /// </summary>
        public string Parent(string v) => _Vs[v];

        /// <summary>
        /// Returns true if the given node has no outgoing edges.
        /// </summary>
        public bool IsLeaf(string node) => !_Us.Keys.Contains(node);

        /// <summary>
        /// IsParent(string u, string v) alias IsAncestor(u, v).
        /// </summary>
        public bool IsParent(string u, string v) => IsAncestor(u, v);

        /// <summary>
        /// Returns true if u is an ancestor of v.
        /// </summary>
        public bool IsAncestor(string u, string v) => _Vs[v] == u;

        /// <summary>
        /// IsChild(string u, string v) alias IsDescendant(u, v).
        /// </summary>
        public bool IsChild(string u, string v) => IsDescendant(u, v);

        /// <summary>
        /// Returns true if u is a descendant of v (i.e., v is an ancestor of u).
        /// </summary>
        public bool IsDescendant(string u, string v) => _Us[u].Contains(v);

        /// <summary>
        /// Returns true if both nodes share the same root.
        /// </summary>
        public bool SameSubtree(string u, string v) => Parent(u) == Parent(v);

        /// <summary>
        /// Returns the size (inclusive) of the subtree rooted at the given node.
        /// </summary>
        public int SubtreeSize(string node) => Subtree(node).Count;

        /// <summary>
        /// Returns the list of nodes from node u down to node v including both.
        /// </summary>
        public List<string> Path(string u, string v) => _Path(u, v);

        /// <summary>
        /// Returns the reverse list of nodes from node u down to node v including both.
        /// </summary>
        public List<string> ReversePath(string u, string v) => _ReversePath(u, v);

        /// <summary>
        /// Returns the list of nodes from the given node up to the root.
        /// Last entry in the list is the root itself.
        /// </summary>
        public List<string> PathToRoot(string node) => _Path(Root, node);

        /// <summary>
        /// Returns the list of nodes from the given node up to the root.
        /// Last entry in the list is the root itself.
        /// </summary>
        public List<string> RootPathTo(string node) => _ReversePath(Root, node);

        /// <summary>
        /// Returns the depth (distance from the root) of the given node.
        /// </summary>
        public int Depth(string node) => PathToRoot(node).Count;

    }
}