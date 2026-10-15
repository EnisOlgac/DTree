using static System.Math;

namespace DirectedTrees {
    public class DList {
        internal DList(String def, string source, string sink) {
            FirstCell = Cells.AddOrGet(source, new Cell() { Def = source, Index = 0 });
            LastCell = Cells.AddOrGet(sink, new Cell() { Def = sink, Index = 0 });
            FirstCell.Next = LastCell;
            LastCell.Prev = FirstCell;
            Def = def;
        }

        internal string Def;

        internal Dictionary<string, Cell> Cells = new();

        internal class Cell {
            internal string Def;
            public Cell Prev { get; internal set; }
            public Cell Next { get; internal set; }
            internal decimal? Index = null;
            public override string ToString() => Def;
        }

        internal Cell FirstCell;
        internal Cell LastCell;
        public string First => FirstCell.Def;
        public string Last => LastCell.Def;

        public string Source => FirstCell?.Def ?? null;
        public string Sink => LastCell?.Def ?? null;

        internal Cell Node(string v) => Cells.Get(v);
        public string Prev(string v) => Node(v)?.Prev?.Def;
        internal Cell Prev(Cell cell) => cell.Prev;
        public string Next(string v) => Node(v)?.Next?.Def;
        internal Cell Next(Cell cell) => cell.Next;
        public decimal? Index(string v) => Node(v)?.Index;

        public bool IsAllocated(string v) => Index(v) != null;
        public bool IsNotAllocated(string v) => !IsAllocated(v);

        public bool IsLeftOf(string v, string u) => Node(v).Index < Node(u).Index;
        public bool IsSelfOrLeftOf(string v, string u) => Node(v).Index <= Node(u).Index;
        public bool IsRightOf(string v, string u) => Node(v).Index > Node(u).Index;
        public bool IsSelfOrRightOf(string v, string u) => Node(v).Index >= Node(u).Index;

        public string InsBefore(string u, string v) {
            if (u == v || u == Source) return (u);
            Cell node = Node(u);
            if (Node(v).Prev == node) return (u);
            if (v == Source) return (InsAfter(u, Source));
            if (IsAllocated(u) && u != Source) {
                node.Next.Prev = node.Prev;
                node.Prev.Next = node.Next;
            }
            return InsBefore(node, Node(v));
        }
        internal string InsBefore(Cell node, Cell next) {
            if (next == LastCell) next.Index += 100;
            node.Index = Middle(next.Index, next.Prev.Index);
            next.Prev.Next = node;
            node.Prev = next.Prev;
            node.Next = next;
            next.Prev = node;
            return node.Def;
        }

        public string InsAfter(string v, string u) {
            if (v == u || v == Sink) return (v);
            Cell node = Node(v);
            if (Node(u).Next == node) return (v);
            if (u == Sink) return (InsBefore(v, Sink));
            if (IsAllocated(v) && v != Sink) {
                node.Prev.Next = node.Next;
                node.Next.Prev = node.Prev;
            }
            return InsAfter(node, Node(u));
        }
        internal string InsAfter(Cell node, Cell prev) {
            if (prev == FirstCell) prev.Index -= 100;
            node.Index = Middle(prev.Next.Index, prev.Index);
            prev.Next.Prev = node;
            node.Next = prev.Next;
            node.Prev = prev;
            prev.Next = node;
            return node.Def;
        }

        internal void Remove(string v) {
            Cell node = Node(v);
            if (node != null) {
                node.Prev.Next = node.Next;
                if (node.Next != null) node.Next.Prev = node.Prev;
                Cells.Remove(v);
            }
        }

        private decimal? Middle(decimal? h, decimal? l) {
            decimal delta = (decimal)(h - l) / 2;
            double m = (double)delta;
            int digits = Max(0, (int)Floor(-Log10(m)));
            decimal rounded = Round(delta, digits, MidpointRounding.AwayFromZero);
            decimal? result = l + rounded;
            if (result <= l || result >= h) result = l + (h - l) / 2;
            return result;
        }

        public override String ToString() {
            var str = Def + ": [";
            var node = FirstCell.Next;
            for (; node != LastCell; node = node.Next) { str += node + (node.Next == LastCell ? "" : ", "); }
            return str + "]";
        }

        internal List<string> ConvertToString() {
            List<string> str = new();
            var node = FirstCell;
            for (; node != null; node = node.Next) { str.Append(node.Def); }
            return str;
        }

        public bool IsSameAs(DList vs) {
            var v = vs.First;
            for (var x = First; x != Last; x = Next(x)) if (x != v) break; else v = vs.Next(v);
            return (v == vs.Last);
        }

    }
}