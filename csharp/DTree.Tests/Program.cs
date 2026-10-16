// Tests and benchmarks for the C# DTree (port of the Python reference implementation 1.1.0).
//
//   dotnet run --project csharp/DTree.Tests -c Release            run all tests
//   dotnet run --project csharp/DTree.Tests -c Release -- bench   run the benchmarks
//
// Every query is checked against a brute-force parent/children model (no projections).

using System.Diagnostics;
using DirectedTrees;

namespace DirectedTrees.Tests {

    internal static class Program {
        private static int _failures;
        private static int _checks;

        private static int Main(string[] args) {
            if (args.Length > 0 && args[0] == "bench") {
                Bench.Run(args.Skip(1).Select(a => int.Parse(a)).ToArray());
                return 0;
            }
            var tests = new (string Name, Action Body)[] {
                ("readme usage", Tests.ReadmeUsage),
                ("insert rules", Tests.InsertRules),
                ("no self reachability", Tests.NoSelfReachability),
                ("two kinds of delete", Tests.TwoKindsOfDelete),
                ("delete root disallowed", Tests.DeleteRootDisallowed),
                ("cut into own subtree rejected", Tests.CutIntoOwnSubtreeRejected),
                ("list level access", Tests.ListLevelAccess),
                ("example files", Tests.ExampleFiles),
                ("DList operations (List.cs)", Tests.DListOperations),
                ("random inserts vs reference", Tests.RandomInserts),
                ("random deletes and moves vs reference", Tests.RandomDeletesAndMoves),
                ("deep chain", Tests.DeepChain),
                ("wide node", Tests.WideNode),
                ("star needs no renumbering", Tests.StarNeedsNoRenumbering),
                ("alternating worst case", Tests.AlternatingWorstCase),
                ("growth at both ends", Tests.GrowthAtBothEnds),
                ("random list operations", Tests.RandomListOperations),
                ("node handles", Tests.NodeHandles),
            };
            var total = Stopwatch.StartNew();
            foreach (var (name, body) in tests) {
                int before = _failures;
                var sw = Stopwatch.StartNew();
                try {
                    body();
                } catch (Exception e) {
                    Fail($"unexpected {e.GetType().Name}: {e.Message}");
                }
                Console.WriteLine($"{(_failures == before ? "ok  " : "FAIL")} {name} ({sw.ElapsedMilliseconds} ms)");
            }
            Console.WriteLine($"\n{tests.Length} tests, {_checks:N0} checks, {_failures} failures, {total.Elapsed.TotalSeconds:F2} s");
            return _failures == 0 ? 0 : 1;
        }

        internal static void Check(bool condition, string message) {
            _checks++;
            if (!condition) Fail(message);
        }

        internal static void Seq<T>(IEnumerable<T> actual, IEnumerable<T> expected, string message) {
            var a = actual.ToList();
            var e = expected.ToList();
            Check(a.SequenceEqual(e), $"{message}: expected [{string.Join(", ", e)}], got [{string.Join(", ", a)}]");
        }

        internal static void Equal<T>(T actual, T expected, string message) =>
            Check(EqualityComparer<T>.Default.Equals(actual, expected), $"{message}: expected {expected}, got {actual}");

        internal static void Throws<TException>(Action action, string message) where TException : Exception {
            try {
                action();
            } catch (TException) {
                _checks++;
                return;
            }
            Fail($"{message}: expected {typeof(TException).Name}");
        }

        private static void Fail(string message) {
            _failures++;
            if (_failures <= 20) Console.WriteLine("     " + message);
        }
    }

    /// <summary>Plain parent/children model mirroring every operation.</summary>
    internal sealed class Reference {
        public readonly Dictionary<string, string> Parent = new();
        public readonly Dictionary<string, List<string>> Children = new();
        public string? Root;

        public void Insert(string u, string v) {
            Root ??= u;
            Parent[v] = u;
            Kids(u).Add(v);
        }

        public void Delete(string v) {
            var p = Parent[v];
            Parent.Remove(v);
            var kids = Children.TryGetValue(v, out var k) ? k : new List<string>();
            Children.Remove(v);
            var sib = Children[p];
            int i = sib.IndexOf(v);
            sib.RemoveAt(i);
            sib.InsertRange(i, kids);
            foreach (var c in kids) Parent[c] = p;
            if (sib.Count == 0) Children.Remove(p);
        }

        public void DeleteSubtree(string v) {
            var stack = new Stack<string>();
            stack.Push(v);
            var gone = new List<string>();
            while (stack.Count > 0) {
                var n = stack.Pop();
                gone.Add(n);
                if (Children.TryGetValue(n, out var kids)) {
                    foreach (var c in kids) stack.Push(c);
                    Children.Remove(n);
                }
            }
            var p = Parent[v];
            Children[p].Remove(v);
            if (Children[p].Count == 0) Children.Remove(p);
            foreach (var n in gone) Parent.Remove(n);
        }

        public void Move(string u, string p) {
            var old = Parent[u];
            Children[old].Remove(u);
            if (Children[old].Count == 0) Children.Remove(old);
            Parent[u] = p;
            Kids(p).Add(u);
        }

        public List<string> Nodes() {
            var list = new List<string> { Root! };
            list.AddRange(Parent.Keys);
            return list;
        }

        public List<string> Ancestors(string v) {   // [v, ..., root]
            var result = new List<string>();
            for (var w = v; ; w = Parent[w]) {
                result.Add(w);
                if (w == Root) break;
            }
            return result;
        }

        public List<string> Preorder(bool reverse) {
            var result = new List<string>();
            var stack = new Stack<string>();
            stack.Push(Root!);
            while (stack.Count > 0) {
                var n = stack.Pop();
                result.Add(n);
                if (!Children.TryGetValue(n, out var kids)) continue;
                IEnumerable<string> order = reverse ? kids : Enumerable.Reverse(kids);
                foreach (var c in order) stack.Push(c);
            }
            return result;
        }

        private List<string> Kids(string u) {
            if (!Children.TryGetValue(u, out var list)) {
                list = new List<string>();
                Children[u] = list;
            }
            return list;
        }
    }

    internal static partial class Tests {
        private static void Check(bool c, string m) => Program.Check(c, m);
        private static void Seq<T>(IEnumerable<T> a, IEnumerable<T> e, string m) => Program.Seq(a, e, m);
        private static void Equal<T>(T a, T e, string m) => Program.Equal(a, e, m);
        private static void Throws<TEx>(Action a, string m) where TEx : Exception => Program.Throws<TEx>(a, m);

        private static void CheckAgainst(DTree t, Reference r, Random rnd) {
            Check(t.Q1.PositionsStrictlyIncrease(), "Q1 positions increase");
            Check(t.Q2.PositionsStrictlyIncrease(), "Q2 positions increase");
            var nodes = r.Nodes();
            Equal(t.Size, nodes.Count, "size");
            Equal(t.Root, r.Root, "root");
            Seq(t.Q1.ToList(), r.Preorder(false), "Q1");
            Seq(t.Q2.ToList(), r.Preorder(true), "Q2");
            foreach (var v in nodes) {
                var anc = r.Ancestors(v);
                Seq(t.PathToRoot(v), anc, $"PathToRoot({v})");
                Equal(t.Depth(v), anc.Count - 1, $"Depth({v})");
                Equal(t.GetParent(v), r.Parent.TryGetValue(v, out var p) ? p : null, $"GetParent({v})");
                Equal(t.IsLeaf(v), !r.Children.ContainsKey(v), $"IsLeaf({v})");
            }
            var sample = nodes.Count <= 40 ? nodes : nodes.OrderBy(_ => rnd.Next()).Take(40).ToList();
            foreach (var u in sample)
                foreach (var v in sample) {
                    bool expected = u != v && r.Ancestors(v).Contains(u);
                    Equal(t.CanReach(u, v), expected, $"CanReach({u}, {v})");
                    Equal(t.IsAncestor(u, v), expected, $"IsAncestor({u}, {v})");
                    Equal(t.IsDescendant(v, u), expected, $"IsDescendant({v}, {u})");
                    Equal(t.CanReach(t.GetNode(u), t.GetNode(v)), expected, $"CanReach(handle {u}, handle {v})");
                }
        }

        private static (DTree, Reference, Random) RandomTree(int n, int seed) {
            var rnd = new Random(seed);
            var t = new DTree("R");
            var r = new Reference();
            var names = new List<string> { "n0" };
            for (int i = 1; i < n; i++) {
                var p = names[rnd.Next(names.Count)];
                t.Insert(p, $"n{i}");
                r.Insert(p, $"n{i}");
                names.Add($"n{i}");
            }
            return (t, r, rnd);
        }

        public static void ReadmeUsage() {
            var t = new DTree("P1");
            t.Insert("A", "B");
            t.Insert("B", "C");
            Check(t.CanReach("A", "C"), "A reaches C");
            Seq(t.PathToRoot("C"), new[] { "C", "B", "A" }, "PathToRoot");
            Seq(t.RootToPath("C"), new[] { "A", "B", "C" }, "RootToPath");
            Equal(t.Root, "A", "Root");
            Equal(t.GetParent("A"), null, "GetParent(root)");
            Equal(t.Depth("A"), 0, "Depth(root)");
            Equal(t.Source, Marker.Source, "Source");
            Equal(t.Sink, Marker.Sink, "Sink");
        }

        public static void InsertRules() {
            var t = new DTree();
            t.Insert("A", "B");
            Throws<KeyNotFoundException>(() => t.Insert("X", "Y"), "parent must exist");
            Throws<ArgumentException>(() => t.Insert("A", "B"), "child must not exist");
        }

        public static void NoSelfReachability() {
            var t = new DTree();
            t.Insert("A", "B");
            foreach (var v in new[] { "A", "B" }) {
                Check(!t.CanReach(v, v), $"CanReach({v},{v}) is false");
                Check(t.CanNotReach(v, v), $"CanNotReach({v},{v})");
                Check(!t.IsAncestor(v, v), $"IsAncestor({v},{v}) is false");
            }
            Seq(t.Subtree("A"), new[] { "A", "B" }, "Subtree(A)");
            Seq(t.Path("A", "A"), new[] { "A" }, "Path(A,A)");
            Throws<InvalidOperationException>(() => t.CutNPaste("B", "B"), "CutNPaste(B,B)");
        }

        public static void TwoKindsOfDelete() {
            static DTree Build() {
                var t = new DTree();
                foreach (var (u, v) in new[] { ("A", "B"), ("B", "C"), ("B", "D"), ("A", "E") }) t.Insert(u, v);
                return t;
            }
            var t1 = Build();
            t1.Delete("B");
            Seq(t1.Children("A"), new[] { "C", "D", "E" }, "children after Delete");
            Seq(t1.Q1.ToList(), new[] { "A", "C", "D", "E" }, "Q1 after Delete");
            var t2 = Build();
            Seq(t2.DeleteSubtree("B"), new[] { "B", "C", "D" }, "DeleteSubtree result");
            Seq(t2.Q1.ToList(), new[] { "A", "E" }, "Q1 after DeleteSubtree");
            Seq(t2.Q2.ToList(), new[] { "A", "E" }, "Q2 after DeleteSubtree");
            Throws<InvalidOperationException>(() => t2.DeleteSubtree("A"), "DeleteSubtree(root)");
        }

        public static void DeleteRootDisallowed() {
            var t = new DTree();
            t.Insert("A", "B");
            Throws<InvalidOperationException>(() => t.Delete("A"), "Delete(root)");
        }

        public static void CutIntoOwnSubtreeRejected() {
            var t = new DTree();
            t.Insert("A", "B");
            t.Insert("B", "C");
            Throws<InvalidOperationException>(() => t.CutNPaste("B", "C"), "CutNPaste into own subtree");
        }

        public static void ListLevelAccess() {
            var t = new DTree();
            t.Insert("A", "B");
            t.Insert("A", "C");
            Check(t.Q1.IsLeftOf("B", "C"), "B left of C in Q1");
            Check(t.Q2.IsLeftOf("C", "B"), "C left of B in Q2");
        }

        public static void ExampleFiles() {
            var dir = FindExamples();
            if (dir == null) { Console.WriteLine("     (examples folder not found, skipped)"); return; }
            foreach (var name in new[] { "Test.csx", "Test1.csx", "test23.csx" }) {
                var path = System.IO.Path.Combine(dir, name);
                if (!File.Exists(path)) continue;
                var t = DTree.FromFile(path);
                Equal(t.Root, "01", $"{name}: root");
                Check(t.CanReach("01", "22"), $"{name}: 01 reaches 22");
                Seq(t.PathToRoot("22"), new[] { "22", "10", "06", "04", "01" }, $"{name}: PathToRoot(22)");
            }
        }

        private static string? FindExamples() {
            for (var d = new DirectoryInfo(AppContext.BaseDirectory); d != null; d = d.Parent) {
                var candidate = System.IO.Path.Combine(d.FullName, "examples");
                if (Directory.Exists(candidate)) return candidate;
            }
            return null;
        }

        public static void DListOperations() {
            var q = new DList("Q");
            Equal(q.Source, Marker.Source, "Source");
            Equal(q.Sink, Marker.Sink, "Sink");
            q.InsertBefore("a", Marker.Sink);
            q.InsertAfter("c", "a");
            q.InsertBefore("b", "c");
            Seq(q.ToList(), new[] { "a", "b", "c" }, "order");
            Seq(q.ToList(true), new[] { Marker.Source, "a", "b", "c", Marker.Sink }, "with markers");
            Check(q.IsLeftOf("a", "c") && q.IsRightOf("c", "a"), "left/right");
            Check(q.IsSelfOrLeftOf("b", "b") && q.IsSelfOrRightOf("b", "b"), "self-or");
            Check(!q.IsLeftOf("b", "b"), "strict");
            Equal(q.Prev("b"), "a", "Prev");
            Equal(q.Next("b"), "c", "Next");
            Check(q.IsAllocated("a") && q.IsNotAllocated("z"), "allocated");
            Check(q.Index("z") == null, "Index of absent node");
            q.InsertBefore("d", Marker.Source);   // redirected to after SOURCE
            q.InsertAfter("e", Marker.Sink);      // redirected to before SINK
            Seq(q.ToList(), new[] { "d", "a", "b", "c", "e" }, "marker redirects");
            q.InsertAfter("a", "a");              // no-op
            q.InsertAfter("b", "a");              // already there: no-op
            q.InsertAfter("d", "c");              // existing node is moved
            Seq(q.ToList(), new[] { "a", "b", "c", "d", "e" }, "move");
            var r = new DList("R");
            foreach (var n in new[] { "a", "b", "c", "d", "e" }) r.InsertBefore(n, Marker.Sink);
            Check(q.IsSameAs(r), "IsSameAs");
            r.Remove("c");
            Check(!q.IsSameAs(r), "not IsSameAs");
        }

        public static void RandomInserts() {
            for (int seed = 0; seed < 30; seed++) {
                var (t, r, rnd) = RandomTree(60, seed);
                CheckAgainst(t, r, rnd);
            }
        }

        public static void RandomDeletesAndMoves() {
            for (int seed = 0; seed < 30; seed++) {
                var (t, r, rnd) = RandomTree(80, seed);
                for (int step = 0; step < 40; step++) {
                    var nodes = r.Nodes().Where(n => n != r.Root).ToList();
                    if (nodes.Count < 10) break;
                    double x = rnd.NextDouble();
                    if (x < 0.35) {
                        var v = nodes[rnd.Next(nodes.Count)];
                        t.Delete(v);
                        r.Delete(v);
                    } else if (x < 0.5) {
                        var v = nodes[rnd.Next(nodes.Count)];
                        var expected = t.Subtree(v);
                        Seq(t.DeleteSubtree(v), expected, "DeleteSubtree result");
                        r.DeleteSubtree(v);
                        foreach (var n in expected) Check(!t.Contains(n), $"{n} removed");
                    } else {
                        var u = nodes[rnd.Next(nodes.Count)];
                        var banned = new HashSet<string>(t.Subtree(u));
                        var targets = r.Nodes().Where(n => !banned.Contains(n)).ToList();
                        var p = targets[rnd.Next(targets.Count)];
                        t.CutNPaste(u, p);
                        r.Move(u, p);
                    }
                    CheckAgainst(t, r, rnd);
                }
            }
        }

        public static void DeepChain() {
            var t = new DTree();
            for (int i = 0; i < 5000; i++) t.Insert($"v{i}", $"v{i + 1}");
            Equal(t.Depth("v5000"), 5000, "depth");
            Check(t.CanReach("v0", "v5000"), "top reaches bottom");
            Check(!t.CanReach("v5000", "v0"), "bottom does not reach top");
            Equal((t.Q1.RenumberCount, t.Q2.RenumberCount), (0L, 0L), "no renumbering for a chain");
        }

        public static void WideNode() {
            var t = new DTree();
            for (int i = 0; i < 5000; i++) t.Insert("r", $"c{i}");
            Equal(t.SubtreeSize("r"), 5001, "subtree size");
            Check(!t.CanReach("c1", "c2"), "siblings unconnected");
            Seq(t.Q2.ToList().Take(3), new[] { "r", "c4999", "c4998" }, "Q2 start");
            Check(t.Q2.PositionsStrictlyIncrease(), "Q2 positions increase");
        }

        public static void StarNeedsNoRenumbering() {
            var t = new DTree();
            t.Insert("r", "x");
            t.Insert("r", "y");
            for (int i = 0; i < 5000; i++) t.Insert("x", $"c{i}");
            Equal((t.Q1.RenumberCount, t.Q2.RenumberCount), (0L, 0L), "no renumbering for a star");
            Check(t.CanReach("x", "c4999"), "x reaches c4999");
            Check(!t.CanReach("c0", "c1"), "siblings unconnected");
        }

        public static void AlternatingWorstCase() {
            var t = new DTree();
            var left = "n0";
            for (int i = 1; i < 4000; i++) {
                t.Insert(left, $"n{i}");
                if (i % 2 == 0) left = $"n{i}";
            }
            Check(t.Q2.RenumberCount > 0, "alternating insertions force renumbering");
            Check(t.Q1.PositionsStrictlyIncrease(), "Q1 positions increase");
            Check(t.Q2.PositionsStrictlyIncrease(), "Q2 positions increase");
            Check(t.Q1.MaxDenominator() <= 1L << 40 && t.Q2.MaxDenominator() <= 1L << 40, "denominators bounded");
        }

        public static void GrowthAtBothEnds() {
            var q = new DList("Q");
            for (int i = 0; i < 5000; i++) {
                q.InsertBefore($"r{i}", Marker.Sink);
                q.InsertAfter($"l{i}", Marker.Source);
            }
            Check(q.PositionsStrictlyIncrease(), "positions increase");
            Seq(q.ToList().Take(2), new[] { "l4999", "l4998" }, "left end");
            Seq(q.ToList().TakeLast(2), new[] { "r4998", "r4999" }, "right end");
            Equal(q.RenumberCount, 0L, "no renumbering");
        }

        public static void RandomListOperations() {
            var rnd = new Random(7);
            var q = new DList("Q");
            var reference = new List<string>();
            for (int i = 0; i < 20000; i++) {
                double x = rnd.NextDouble();
                if (reference.Count > 0 && x < 0.15) {
                    var v = reference[rnd.Next(reference.Count)];
                    q.Remove(v);
                    reference.Remove(v);
                    continue;
                }
                var name = $"v{i}";
                if (reference.Count == 0 || x < 0.25) {
                    q.InsertAfter(name, Marker.Source);
                    reference.Insert(0, name);
                } else {
                    // hammer a few hot spots to force renumbering
                    int[] spots = { 0, reference.Count / 2, reference.Count - 1, rnd.Next(reference.Count) };
                    int j = spots[rnd.Next(spots.Length)];
                    if (rnd.NextDouble() < 0.5) {
                        q.InsertAfter(name, reference[j]);
                        reference.Insert(j + 1, name);
                    } else {
                        q.InsertBefore(name, reference[j]);
                        reference.Insert(j, name);
                    }
                }
            }
            Seq(q.ToList(), reference, "order matches a plain list");
            Check(q.PositionsStrictlyIncrease(), "positions increase");
        }
    }

    internal static partial class Tests {
        public static void NodeHandles() {
            var t = new DTree();
            var b = t.Insert("A", "B");
            var c = t.Insert(b, "C");
            var d = t.Insert("A", "D");
            var a = t.GetNode("A");
            Equal(b.Name, "B", "Insert returns the child's handle");
            Check(t.CanReach(a, c) && t.CanReach(b, c), "handles: ancestors reach C");
            Check(!t.CanReach(c, a) && !t.CanReach(b, d) && !t.CanReach(c, c), "handles: no other reachability");
            Check(t.IsRoot(a) && !t.IsRoot(b), "IsRoot on handles");
            Equal(t.Depth(c), 2, "Depth on handle");
            Check(c.Parent == b && a.Parent == null, "Parent on handles");
            Seq(a.Children.Select(n => n.Name), new[] { "B", "D" }, "Children on handle");
            Check(t.TryGetNode("D", out var d2) && d2 == d && !t.TryGetNode("X", out _), "TryGetNode");
            t.CutNPaste(c, d);
            Check(t.CanReach(d, c) && !t.CanReach(b, c), "CutNPaste on handles");
            t.Delete(b);
            Check(!b.IsInTree && !t.CanReach(a, b), "deleted handle no longer reaches or is reached");
            Throws<ArgumentException>(() => t.Insert(b, "E"), "Insert under a deleted handle");
            var other = new DTree("other");
            var x = other.Insert("X", "Y");
            Check(!t.CanReach(a, x), "handles of another tree are not reachable");
            Throws<ArgumentException>(() => t.Delete(x), "Delete with a handle of another tree");
            Equal(t.DeleteSubtree(d).Count, 2, "DeleteSubtree on handle removes D and C");
            Check(!c.IsInTree && t.Size == 1, "only the root is left");
        }
    }

    internal static class Bench {
        private static readonly (string Name, Func<int, List<string>, Random, string> Parent)[] Shapes = {
            ("random", (i, names, rnd) => names[rnd.Next(names.Count)]),
            ("chain", (i, names, rnd) => names[^1]),
            ("star (root)", (i, names, rnd) => "n0"),
            ("star (inner node)", (i, names, rnd) => i <= 2 ? "n0" : "n1"),
            ("alternating", (i, names, rnd) => $"n{2 * ((i - 1) / 2)}"),
        };

        private static (DTree Tree, List<string> Names, double Seconds) Build(int shape, int n, int seed = 1) {
            var rnd = new Random(seed);
            var t = new DTree("B");
            var names = new List<string> { "n0" };
            var sw = Stopwatch.StartNew();
            for (int i = 1; i < n; i++) {
                t.Insert(Shapes[shape].Parent(i, names, rnd), $"n{i}");
                names.Add($"n{i}");
            }
            return (t, names, sw.Elapsed.TotalSeconds);
        }

        public static void Run(int[] sizes) {
            if (sizes.Length == 0) sizes = new[] { 10_000, 100_000 };
            Console.WriteLine($"DTree benchmarks (C#, .NET {Environment.Version})\n");
            Console.WriteLine("| shape | nodes | time [s] | renumberings Q1 / Q2 | positions moved per insertion |");
            Console.WriteLine("| --- | ---: | ---: | ---: | ---: |");
            for (int s = 0; s < Shapes.Length; s++)
                foreach (var n in sizes) {
                    var (t, _, sec) = Build(s, n);
                    double moved = (t.Q1.RenumberMoved + t.Q2.RenumberMoved) / (2.0 * n);
                    Console.WriteLine($"| {Shapes[s].Name} | {n:N0} | {sec:F3} | {t.Q1.RenumberCount:N0} / {t.Q2.RenumberCount:N0} | {moved:F2} |");
                }

            int big = sizes.Max();
            var (tree, nodes, _) = Build(0, big);
            var rnd = new Random(2);
            const int queries = 1_000_000;
            var pairs = new (string, string)[queries];
            for (int i = 0; i < queries; i++) pairs[i] = (nodes[rnd.Next(nodes.Count)], nodes[rnd.Next(nodes.Count)]);
            var sw = Stopwatch.StartNew();
            int hits = 0;
            foreach (var (u, v) in pairs) if (tree.CanReach(u, v)) hits++;
            double perQuery = sw.Elapsed.TotalMilliseconds * 1000 / queries;
            Console.WriteLine($"\nCanReach on a random tree of {big:N0} nodes: {perQuery:F3} µs per call with names ({hits:N0} of {queries:N0} reachable)");
            var handles = new (DNode, DNode)[queries];
            for (int i = 0; i < queries; i++) handles[i] = (tree.GetNode(pairs[i].Item1), tree.GetNode(pairs[i].Item2));
            sw.Restart();
            int hits2 = 0;
            foreach (var (u, v) in handles) if (tree.CanReach(u, v)) hits2++;
            double perHandle = sw.Elapsed.TotalMilliseconds * 1000 / queries;
            Console.WriteLine($"CanReach on a random tree of {big:N0} nodes: {perHandle:F3} µs per call with node handles ({hits2:N0} reachable)");
        }
    }
}
