using static System.Math;
using static DirectedTrees.Extensions;

namespace DirectedTrees {
    public partial class DTree {
        /// <summary>
        /// Represents a directed tree of uniquely identified vertices of type V.
        /// Supports symbolic projections and incremental construction.
        /// </summary>
        internal DTree(string? def = null) {
            _Def = def ?? "P1";
            _Q1 = new(this._Def + ".Q1", _Source, _Sink);
            _Q2 = new(this._Def + ".Q2", _Source, _Sink);
        }

        public string _Def { get; internal set; }
        internal string _EdgeLog = "";
        private bool _Initialized = false;

        public Dictionary<string, List<string>> _Us { get; internal set; } = new();
        public Dictionary<string, string> _Vs { get; internal set; } = new();
        public string Pred(string v) => _Vs.Get(v);
        public List<string> Succs(string v) => _Us.Get(v) ?? new();
        public bool _Succ(string v, string u) => Succs(u).Contains<string>(v);
        public bool NotSucc(string v, string u) => !_Succ(v, u);

        internal DList _Q1 { get; private set; }
        internal DList _Q2 { get; private set; }

        internal string _Source { get; private set; } = "[";
        internal string _Sink { get; private set; } = "]";

        public Dictionary<(string, string), _Edge> _Edges { get; internal set; } = new();

        public void _Root(string u) {
            if (!_Vs.Exists(u)) {
                if (!_Initialized) {
                    _AddEdge(_Source, u);
                    _InsTreeEdge(_Source, u);
                    _Initialized = true;
                } else throw new ArgumentException("Edge already exist.");
            }
        }

        internal void _InsEdge(string u, string v) {
            if (_Edges.Exists((u, v))) return;
            _AddCell(u);
            _AddCell(v);
            if (!_Initialized) _Root(u); else if (!_Vs.Exists(u)) throw new ArgumentException("Vertex u : " + u + " not defined.");
            if (_Vs.Exists(v)) throw new ArgumentException("Edge already exist.");
            _InsTreeEdge(u, v);
            _EdgeLog += _AddEdge(u, v) + "\n";
        }

        public _Edge _AddEdge(string u, string v) {
            _Edge e;
            e = _Edges.AddOrGet((u, v), e = new _Edge(u, v));
            _UpdPredNSucc(u, v);
            return e;
        }

        public bool _IsAllocated(string v) => v != null && _Q1.IsAllocated(v) && _Q2.IsAllocated(v);
        public bool _IsNotAllocated(string v) => !_IsAllocated(v);

        internal bool _CanReach(string u, string v) => _IsAllocated(u) && _IsAllocated(v) && (_Q1.IsSelfOrLeftOf(u, v) && _Q2.IsSelfOrLeftOf(u, v));
        internal bool _CanNotReach(string u, string v) => !_CanReach(u, v);

        public List<string> _Subtree(string u) {
            List<string> nodes = new();
            var v = u;
            for (; CanReach(u, v) && v != Sink; v = _Q1.Next(v)) nodes.Append(v);
            return nodes;
        }

        public List<string> _Path(string u, string v) {
            List<string> nodes = new();
            var w = v;
            for (; _Vs[w] != u; w = _Vs[w]) nodes.Prepend(w);
            nodes.Prepend(u);
            return nodes;
        }

        public List<string> _ReversePath(string u, string v) {
            List<string> nodes = new();
            var w = v;
            for (; _Vs[w] != u; w = _Vs[w]) nodes.Append(w);
            nodes.Prepend(u);
            return nodes;
        }

        public List<string> _PathToRoot(string v) {
            List<string> nodes = new();
            return nodes;
        }

        public List<string> _RootToPath(string v, DList qq) {
            List<string> nodes = new();
            var u = qq.First;
            for (; _Vs[u] != Source; u = _Vs[u]) nodes.Prepend(u);
            return nodes;
        }

        public string _LastCanReach(string u, DList qq) {
            var v = qq.Prev(qq.Last);
            for (; v != null && _CanNotReach(u, v); v = qq.Prev(v)) ;
            return v;
        }

        internal string _Delimiter(string u, DList qq) {
            var v = u;
            for (; v != qq.Last && _CanReach(u, v); v = qq.Next(v)) ;
            return v;
        }

        internal void _InsTreeEdge(string u, string v) {
            _Q2.InsAfter(v, u);
            var last = _Delimiter(u, _Q1);
            _Q1.InsBefore(v, last);
        }

        internal void _UpdPredNSucc(string u, string v) {
            _Vs.AddOrUpd(v, u);
            _Us.AddOrGet(u, new List<string>()).AppendIfAbsent(v);
        }

        internal void _AddCell(string v) {
            _Q1.Cells.AddOrGet(v, new DList.Cell() { Def = v });
            _Q2.Cells.AddOrGet(v, new DList.Cell() { Def = v });
        }
    }

    public class _Edge {
        public _Edge(string u, string v) {
            _Tail = u;
            _Head = v;
            _Type = EdgeType.Tree;
        }

        public string _Def => "(" + _Tail + ", " + _Head + ")";
        public string _Tail { get; }
        public string _Head { get; }
        public EdgeType _Type { get; set; }
        public void Deconstruct(out string u, out string v) { u = _Tail; v = _Head; }
        public override string ToString() => _Def;
    }

}