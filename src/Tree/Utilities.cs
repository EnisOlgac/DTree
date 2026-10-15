namespace DirectedTrees {
    public static class Extensions {
        public enum EdgeType { Back, For, Tree, Cross, Dup, Default }
        public static List<T> AppendIfAbsent<T>(this List<T> list, T e) {
            if (list.Contains(e)) { } else { list.Append(e); }
            return (list);
        }
        public static V AddOrGet<K, V>(this Dictionary<K, V> dict, K key, V nValue) {
            if (dict.TryGetValue(key, out var value)) { nValue = value; } else { dict.Add(key, nValue); }
            return (nValue);
        }
        public static List<T> AddOrGet<K, T>(this Dictionary<K, List<T>> dict, K key, List<T> nValue) {
            if (dict.TryGetValue(key, out var value)) { nValue = value; } else { dict.Add(key, nValue); }
            return (nValue);
        }
        public static V AddOrUpd<K, V>(this Dictionary<K, V> dict, K key, V nValue) {
            if (dict.TryAdd(key, nValue)) { } else { dict[key] = nValue; }
            return (nValue);
        }
        public static V Get<K, V>(this Dictionary<K, V> dict, K key) {
            if (key == null) return (default);
            if (!dict.TryGetValue(key, out var value)) { return (default); }
            return (value);
        }
        public static bool Exists<K, V>(this Dictionary<K, V> dict, K key) {
            return (dict.TryGetValue(key, out var _));
        }
        public static List<T> Append<T>(this List<T> list, T e) {
            list.Add(e);
            return (list);
        }
        public static List<T> Prepend<T>(this List<T> list, T e) {
            list.Insert(0, e);
            return (list);
        }
    }
}