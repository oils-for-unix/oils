#ifndef OLDSTL_DICT_H
#define OLDSTL_DICT_H

// Dict currently implemented by VECTOR OF PAIRS.  TODO: Use a real hash table,
// and measure performance.  The hash table has to beat this for small cases!
template <class K, class V>
class Dict : public Obj {
 public:
  Dict() : Obj(Tag::FixedSize, kZeroMask, 0), items_() {
  }

  // Dummy
  Dict(std::initializer_list<K> keys, std::initializer_list<V> values)
      : Obj(Tag::FixedSize, kZeroMask, 0), items_() {
  }

  // d[key] in Python: raises KeyError if not found
  V index_(K key);

  // Get a key.
  // Returns nullptr if not found (Can't use this for non-pointer types?)
  V get(K key);

  // Get a key, but return a default if not found.
  // expr_parse.py uses this with OTHER_BALANCE
  V get(K key, V default_val);

  // d->set(key, val) is like (*d)[key] = val;
  void set(K key, V val);

  void remove(K key);

  List<K>* keys();

  // For AssocArray transformations
  List<V>* values();

  void clear();

  // std::unordered_map<K, V> m_;
  std::vector<std::pair<K, V>> items_;

 private:

  // returns the position in the array
  int find(K key);
};
#endif  // OLDSTL_CONTAINERS_H
