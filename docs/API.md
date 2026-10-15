# DTree Public API Reference

*Markdown edition of [`User.Doc.pdf`](User.Doc.pdf).*

## Overview

The `DTree` class represents a symbolic directed tree with a unique root and internal support for dual projections (Q1 and Q2). Each node is identified by a unique string. Edges are added incrementally, and projections are updated automatically. Structural operations preserve the tree's topological validity.

## Constructor

### `DTree(string id)`
Create a new tree with a given identifier.
- Initializes a new directed tree with the given identifier.
- The root is determined implicitly as the source of the first inserted edge.
- Q1 and Q2 projections are initialized automatically.

## Core Methods

### `void Insert(string parent, string child)`
Insert a new edge into the tree.
- Adds a directed edge from `parent` to `child`.
- The `parent` must already exist in the tree.
- The `child` must not already exist.
- Updates Q1 and Q2 projections accordingly.

### `bool Contains(string node)`
Check if a node exists.
- Returns `true` if the specified node is present in the tree.
- Otherwise returns `false`.

### `string GetParent(string node)`
Return the parent of a node.
- Returns the parent of `node`.
- If `node` is the root, returns `null`.
- Throws an error if the node is not found.

## Structural Reconfiguration

### `void CutNPaste(string u1, string u2)`
Detach a subtree from its root and attach it to another.
- Extracts the subtree rooted at `u2` from the tree rooted at `u1`.
- The subtree is detached from its original parent and reattached under a new one.
- Ensures that no orphaned structure remains in the source tree.
- Both source and destination trees must be structurally valid after the operation.

### `void Delete(string node)`
Remove a node and reattach its children, if any, to its parent.
- Deletes `node` from the tree.
- If `node` has children, they are reattached to `RootOf(node)`.
- Behaves as a shorthand for `CutNPaste(node, RootOf(node))`.
- If `node` is the root, the operation is disallowed.

## Accessors

### `DList Q1`
Return the Q1 projection.
- Returns a copy of the Q1 projection (left-to-right traversal).
- The projection reflects the current visible tree state.

### `DList Q2`
Return the Q2 projection.
- Returns a copy of the Q2 projection (right-to-left traversal).
- Q2 is the sibling-reversed counterpart of Q1.

### `string Source`
Return the symbolic source node.
- Returns the symbolic start marker of all projections.
- This node is **not** part of the tree structure.
- It conceptually acts as the left bracket delimiting Q1 and Q2.

### `string Sink`
Return the symbolic sink node.
- Returns the symbolic end marker of all projections.
- This node is **not** part of the tree structure.
- It conceptually acts as the right bracket delimiting Q1 and Q2.

## Query Methods

### Reachability

#### `bool CanReach(string u, string v)`
Check if one node can reach another.
- Returns `true` if there is a directed path from node `u` to node `v`.
- The check is structural and respects tree hierarchy.

#### `bool CanNotReach(string u, string v)`
Check if one node cannot reach another.
- Returns `true` if there is no directed path from node `u` to node `v`.
- Logical negation of `CanReach(u, v)`.

### Ancestry and Structure

#### `bool IsRoot(string node)`
- Returns `true` if `node` is the root of the tree.

#### `bool IsLeaf(string node)`
- Returns `true` if `node` has no outgoing edges.

#### `bool IsAncestor(string u, string v)`
- Returns `true` if node `u` lies on the path from the root to node `v`.

#### `bool IsDescendant(string u, string v)`
- Returns `true` if node `u` lies below node `v` in the tree.
- Equivalent to `IsAncestor(v, u)`.

#### `bool SameSubtree(string u, string v)`
- Returns `true` if both nodes share the same root.
- Useful for validating `CutNPaste` targets.

#### `int SubtreeSize(string node)`
- Returns the size (inclusive) of the subtree rooted at `node`.
- Includes the node itself and all its descendants.

#### `int Depth(string node)`
- Returns the distance from the root to `node`.
- The root has depth 0.

#### `List<string> PathToRoot(string node)`
- Returns the sequence of nodes on the path from `node` to the root.
- The last entry in the list is the root itself.

#### `List<string> RootToPath(string node)`
- Returns the sequence of nodes on the path from the root to `node`.
- The first entry in the list is the root itself.
