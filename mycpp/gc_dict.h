#ifndef GC_DICT_H
#define GC_DICT_H

// Non-negative entries in entry_ are array indices into keys_ and values_.
// There are two special negative entries.

// index that means this Dict item was deleted (a tombstone).
const int kDeletedEntry = -1;

// index that means this Dict entry is free.  Because we have Dict[int, int],
// we can't use a sentinel entry in keys_.  It has to be a sentinel entry in
// entry_.
const int kEmptyEntry = -2;

// Helper for keys() and values()
template <typename T>
List<T>* ListFromDictSlab(Slab<int>* index, Slab<T>* slab, int n) {
  // TODO: Reserve the right amount of space
  List<T>* result = nullptr;
  StackRoots _roots({&index, &slab, &result});

  result = Alloc<List<T>>();

  for (int i = 0; i < n; ++i) {
    int special = index->items_[i];
    if (special == kDeletedEntry) {
      continue;
    }
    if (special == kEmptyEntry) {
      break;
    }
    result->append(slab->items_[i]);
  }
  return result;
}

// Type that is layout-compatible with List to avoid invalid-offsetof warnings.
// Unit tests assert that they have the same layout.
class _DummyDict {
 public:
  OBJ_HEADER()
  int len_;
  int capacity_;
  void* entry_;
  void* keys_;
  void* values_;
};

// A list has one Slab pointer which we need to follow.
constexpr uint16_t maskof_Dict() {
  return maskbit(offsetof(_DummyDict, entry_)) |
         maskbit(offsetof(_DummyDict, keys_)) |
         maskbit(offsetof(_DummyDict, values_));
}

template <class K, class V>
class Dict : public Obj {
 public:
  Dict() : Obj(Tag::FixedSize, maskof_Dict(), sizeof(Dict)) {
    assert(len_ == 0);
    assert(capacity_ == 0);
    assert(entry_ == nullptr);
    assert(keys_ == nullptr);
    assert(values_ == nullptr);
  }

  Dict(std::initializer_list<K> keys, std::initializer_list<V> values)
    : Obj(Tag::FixedSize, maskof_Dict(), sizeof(Dict))
  {
    assert(len_ == 0);
    assert(capacity_ == 0);
    assert(entry_ == nullptr);
    assert(keys_ == nullptr);
    assert(values_ == nullptr);
  }

  // This relies on the fact that containers of 4-byte ints are reduced by 2
  // items, which is greater than (or equal to) the reduction of any other
  // type
  static const int kCapacityAdjust = kSlabHeaderSize / sizeof(int);
  static_assert(kSlabHeaderSize % sizeof(int) == 0,
                "Slab header size should be multiple of key size");

  void reserve(int n);

  // d[key] in Python: raises KeyError if not found
  V index_(K key);

  // Get a key.
  // Returns nullptr if not found (Can't use this for non-pointer types?)
  V get(K key);

  // Get a key, but return a default if not found.
  // expr_parse.py uses this with OTHER_BALANCE
  V get(K key, V default_val);

  // Implements d[k] = v.  May resize the dictionary.
  //
  // TODO: Need to specialize this for StackRoots!  Gah!
  void set(K key, V val);

  void remove(K key);

  List<K>* keys();

  // For AssocArray transformations
  List<V>* values();

  void clear();

  // Returns the position in the array.  Used by dict_contains(), index(),
  // get(), and set().
  //
  // For now this does a linear search.
  // TODO:
  // - hash functions, and linear probing.
  // - resizing based on load factor
  //   - which requires rehashing (re-insert all items)
  // - Special case to intern Str* when it's hashed?  How?
  //   - Should we have wrappers like:
  //   - V GetAndIntern<V>(D, &string_key)
  //   - SetAndIntern<V>(D, &string_key, value)
  //   This will enable duplicate copies of the string to be garbage collected
  int position_of_key(K key);

  // int index_size_;  // size of index (sparse)
  int len_;       // number of entries (keys and values, almost dense)
  int capacity_;  // number of entries before resizing

  // These 3 slabs are resized at the same time.
  Slab<int>* entry_;  // NOW: kEmptyEntry, kDeletedEntry, or 0.
                      // LATER: indices which are themselves indexed by // hash
                      // value % capacity_
  Slab<K>* keys_;     // Dict<int, V>
  Slab<V>* values_;   // Dict<K, int>

  DISALLOW_COPY_AND_ASSIGN(Dict)
};

template <typename K, typename V>
inline bool dict_contains(Dict<K, V>* haystack, K needle) {
  return haystack->position_of_key(needle) != -1;
}

template <typename K, typename V>
Dict<K, V>* NewDict() {
  auto self = Alloc<Dict<K, V>>();
  return self;
}

template <typename K, typename V>
Dict<K, V>* NewDict(std::initializer_list<K> keys,
                    std::initializer_list<V> values) {
  assert(keys.size() == values.size());
  auto self = Alloc<Dict<K, V>>();
  StackRoots _roots({&self});

  auto v = values.begin();  // This simulates a "zip" loop
  for (auto key : keys) {
    self->set(key, *v);
    ++v;
  }

  return self;
}


#endif
