// Hash table based on CPython's "compact dict":
//
//   https://mail.python.org/pipermail/python-dev/2012-December/123028.html
//   https://code.activestate.com/recipes/578375/
//
// Main differences:
// - It's type-specialized in C++ -- Dict<K, V>.
// - It's integrated with our mark and sweep GC, using Slab<int>, Slab<K>, and
//   Slab<V>
// - We use linear probing, not the pseudo-random number generator

#ifndef MYCPP_GC_DICT_H
#define MYCPP_GC_DICT_H

#include "mycpp/comparators.h"
#include "mycpp/gc_builtins.h"
#include "mycpp/gc_list.h"
#include "mycpp/hash.h"

// Non-negative entries in index_ are array indices into keys_ and values_.
// There are two special negative entries:

// index_ value to say this Dict item was deleted (a tombstone).
const int kDeletedEntry = -1;

// index_ value to say this Dict entry is free.
const int kEmptyEntry = -2;

// Return value for find_kv_index(), not stored in index_.
const int kNotFound = -3;

// Return value for hash_and_probe(), not stored in index_.
const int kTooSmall = -4;

// Helper for keys() and values()
template <typename T>
List<T>* ListFromDictSlab(Slab<T>* slab, int n) {
  List<T>* result = Alloc<List<T>>();
  result->reserve(n);

  for (int i = 0; i < n; ++i) {
    result->append(slab->items_[i]);
  }
  return result;
}

// GlobalDict is layout-compatible with Dict (unit tests assert this), and it
// can be a true C global (incurs zero startup time)

template <typename K, typename V, int N>
class GlobalDict {
 public:
  int len_;
  int capacity_;
  int index_len_;
  GlobalSlab<int, N>* index_;
  GlobalSlab<K, N>* keys_;
  GlobalSlab<V, N>* values_;
};

#define GLOBAL_DICT(name, K, V, N, keys, vals)                                 \
  GcGlobal<GlobalSlab<K, N>> _keys_##name = {ObjHeader::Global(TypeTag::Slab), \
                                             {.items_ = keys}};                \
  GcGlobal<GlobalSlab<V, N>> _vals_##name = {ObjHeader::Global(TypeTag::Slab), \
                                             {.items_ = vals}};                \
  GcGlobal<GlobalDict<K, V, N>> _dict_##name = {                               \
      ObjHeader::Global(TypeTag::Dict),                                        \
      {.len_ = N,                                                              \
       .capacity_ = N,                                                         \
       .index_len_ = 0,                                                        \
       .index_ = nullptr,                                                      \
       .keys_ = &_keys_##name.obj,                                             \
       .values_ = &_vals_##name.obj},                                          \
  };                                                                           \
  Dict<K, V>* name = reinterpret_cast<Dict<K, V>*>(&_dict_##name.obj);

template <class K, class V>
class Dict {
 public:
  Dict()
      : len_(0),
        capacity_(0),
        index_len_(0),
        index_(nullptr),
        keys_(nullptr),
        values_(nullptr) {
  }

  Dict(std::initializer_list<K> keys, std::initializer_list<V> values)
      : len_(0),
        capacity_(0),
        index_len_(0),
        index_(nullptr),
        keys_(nullptr),
        values_(nullptr) {
    DCHECK(keys.size() == values.size());
    auto v = values.begin();  // This simulates a "zip" loop
    for (auto key : keys) {
      // note: calls reserve(), and may allocate
      this->set(key, *v);
      ++v;
    }
  }

  // Reserve enough space for at LEAST this many key-value pairs.
  void reserve(int num_desired);

  // d[key] in Python: raises KeyError if not found
  V at(K key) const;

  // d.get(key) in Python. (Can't use this if V isn't a pointer!)
  V get(K key) const;

  // Get a key, but return a default if not found.
  // expr_parse.py uses this with OTHER_BALANCE
  V get(K key, V default_val) const;

  // Implements d[k] = v.  May resize the dictionary.
  void set(K key, V val);

  void update(List<Tuple2<K, V>*>* pairs);
  void update(Dict<K, V>* other);

  List<K>* keys() const;

  List<V>* values() const;

  void clear();

  // Helper used by find_kv_index(), set(), mylib::dict_erase() in
  // gc_mylib.h
  // Returns either:
  // - the slot for an existing key, or an empty slot for a new key
  // - kTooSmall if the table is full
  int hash_and_probe(K key) const;

  // Helper used by at(), get(), dict_contains()
  // Given a key, returns either:
  // - an index into keys_ and values_
  // - kNotFound
  int find_kv_index(K key) const;

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(Dict));
  }

  int len_;        // number of entries (keys and values, almost dense)
  int capacity_;   // number of k/v slots
  int index_len_;  // number of index slots

  // These 3 slabs are resized at the same time.
  Slab<int>* index_;  // kEmptyEntry, kDeletedEntry, or a valid index into
                      // keys_ and values_
  Slab<K>* keys_;     // Dict<K, int>
  Slab<V>* values_;   // Dict<int, V>

  // A dict has 3 pointers the GC needs to follow.
  static constexpr uint32_t field_mask() {
    return maskbit(offsetof(Dict, index_)) | maskbit(offsetof(Dict, keys_)) |
           maskbit(offsetof(Dict, values_));
  }

  DISALLOW_COPY_AND_ASSIGN(Dict);

  // kItemSize is max of K and V size.  That is, on 64-bit machines, the RARE
  // Dict<int, int> is smaller than other dicts
  static constexpr int kItemSize = sizeof(K) > sizeof(V) ? sizeof(K)
                                                         : sizeof(V);

  // Matches mark_sweep_heap.h
  static constexpr int kPoolBytes2 = 48 - sizeof(ObjHeader);
  static_assert(kPoolBytes2 % kItemSize == 0,
                "An integral number of items should fit in second pool");
  static constexpr int kNumItems2 = kPoolBytes2 / kItemSize;

  static const int kHeaderFudge = sizeof(ObjHeader) / kItemSize;
  static_assert(sizeof(ObjHeader) % kItemSize == 0,
                "Slab header size should be multiple of key size");

#if 0
  static constexpr int kMinBytes2 = 128 - sizeof(ObjHeader);
  static_assert(kMinBytes2 % kItemSize == 0,
                "An integral number of items should fit");
  static constexpr int kMinItems2 = kMinBytes2 / kItemSize;
#endif

  int HowManyPairs(int num_desired) {
    // See gc_list.h for comments on nearly identical logic

    if (num_desired <= kNumItems2) {  // use full cell in pool 2
      return kNumItems2;
    }
#if 0
    if (num_desired <= kMinItems2) {  // 48 -> 128, not 48 -> 64
      return kMinItems2;
    }
#endif
    return RoundUp(num_desired + kHeaderFudge) - kHeaderFudge;
  }
};

template <typename K, typename V>
inline bool dict_contains(const Dict<K, V>* haystack, K needle) {
  return haystack->find_kv_index(needle) != kNotFound;
}

template <typename K, typename V>
void Dict<K, V>::reserve(int num_desired) {
  if (capacity_ >= num_desired) {
    return;  // Don't do anything if there's already enough space.
  }

  int old_len = len_;
  Slab<K>* old_k = keys_;
  Slab<V>* old_v = values_;

  // Calculate the number of keys and values we should have
  capacity_ = HowManyPairs(num_desired);

  // 1) Ensure index len a power of 2, to avoid expensive modulus % operation
  // 2) Introduce hash table load factor.   Use capacity_+1 to simulate ceil()
  // div, not floor() div.
  index_len_ = RoundUp((capacity_ + 1) * 5 / 4);
  DCHECK(index_len_ > capacity_);

  index_ = NewSlab<int>(index_len_);
  for (int i = 0; i < index_len_; ++i) {
    index_->items_[i] = kEmptyEntry;
  }

  // These are DENSE, while index_ is sparse.
  keys_ = NewSlab<K>(capacity_);
  values_ = NewSlab<V>(capacity_);

  if (old_k != nullptr) {  // rehash if there were any entries
    // log("REHASH num_desired %d", num_desired);
    len_ = 0;
    for (int i = 0; i < old_len; ++i) {
      set(old_k->items_[i], old_v->items_[i]);
    }
  }
}

template <typename K, typename V>
V Dict<K, V>::at(K key) const {
  int kv_index = find_kv_index(key);
  if (kv_index == kNotFound) {
    throw Alloc<KeyError>();
  } else {
    return values_->items_[kv_index];
  }
}

template <typename K, typename V>
V Dict<K, V>::get(K key) const {
  int kv_index = find_kv_index(key);
  if (kv_index == kNotFound) {
    return nullptr;
  } else {
    return values_->items_[kv_index];
  }
}

template <typename K, typename V>
V Dict<K, V>::get(K key, V default_val) const {
  int kv_index = find_kv_index(key);
  if (kv_index == kNotFound) {
    return default_val;
  } else {
    return values_->items_[kv_index];
  }
}

template <typename K, typename V>
List<K>* Dict<K, V>::keys() const {
  return ListFromDictSlab<K>(keys_, len_);
}

template <typename K, typename V>
List<V>* Dict<K, V>::values() const {
  return ListFromDictSlab<V>(values_, len_);
}

template <typename K, typename V>
void Dict<K, V>::clear() {
  // Maintain invariant
  for (int i = 0; i < index_len_; ++i) {
    index_->items_[i] = kEmptyEntry;
  }

  if (keys_) {
    memset(keys_->items_, 0, len_ * sizeof(K));  // zero for GC scan
  }
  if (values_) {
    memset(values_->items_, 0, len_ * sizeof(V));  // zero for GC scan
  }
  len_ = 0;
}

// TODO:
// - Special case to intern BigStr* when it's hashed?  How?
//   - Should we have wrappers like:
//   - V GetAndIntern<V>(D, &string_key)
//   - SetAndIntern<V>(D, &string_key, value)
//   This will enable duplicate copies of the string to be garbage collected
template <typename K, typename V>
int Dict<K, V>::hash_and_probe(K key) const {
  if (capacity_ == 0) {
    return kTooSmall;
  }

  // Hash the key onto a slot in the index. If the first slot is occupied,
  // probe until an empty one is found.
  unsigned h = hash_key(key);
  // faster % using & -- assuming index_len_ is power of 2
  int init_bucket = h & (index_len_ - 1);

  // If we see a tombstone along the probing path, stash it.
  int open_slot = -1;

  for (int i = 0; i < index_len_; ++i) {
    // Start at init_bucket and wrap araound

    // faster % using & -- assuming index_len_ is power of 2
    int slot = (i + init_bucket) & (index_len_ - 1);

    int kv_index = index_->items_[slot];
    DCHECK(kv_index < len_);
    // Optimistically this is the common case once the table has been populated.
    if (kv_index >= 0) {
      unsigned h2 = hash_key(keys_->items_[kv_index]);
      if (h == h2 && keys_equal(keys_->items_[kv_index], key)) {
        return slot;
      }
    }

    if (kv_index == kEmptyEntry) {
      if (open_slot != -1) {
        slot = open_slot;
      }
      // If there isn't room in the entry arrays, tell the caller to resize.
      return len_ < capacity_ ? slot : kTooSmall;
    }

    // Tombstone or collided keys unequal. Keep scanning.
    DCHECK(kv_index >= 0 || kv_index == kDeletedEntry);
    if (kv_index == kDeletedEntry && open_slot == -1) {
      // NOTE: We only record the open slot here. We DON'T return it. If we're
      // looking for a key that was writen before this tombstone was written to
      // the index we should continue probing until we get to that key. If we
      // get to an empty index slot or the end of the index then we know we are
      // dealing with a new key and can safely replace the tombstone without
      // disrupting any existing keys.
      open_slot = slot;
    }
  }

  if (open_slot != -1) {
    return len_ < capacity_ ? open_slot : kTooSmall;
  }

  return kTooSmall;
}

template <typename K, typename V>
int Dict<K, V>::find_kv_index(K key) const {
  if (index_ != nullptr) {  // Common case
    int pos = hash_and_probe(key);
    if (pos == kTooSmall) {
      return kNotFound;
    }
    DCHECK(pos >= 0);
    int kv_index = index_->items_[pos];
    if (kv_index < 0) {
      return kNotFound;
    }
    return kv_index;
  }

  // Linear search on GlobalDict instances.
  // TODO: Should we populate and compare their hash values?
  for (int i = 0; i < len_; ++i) {
    if (keys_equal(keys_->items_[i], key)) {
      return i;
    }
  }

  return kNotFound;
}

template <typename K, typename V>
void Dict<K, V>::set(K key, V val) {
  DCHECK(obj_header().heap_tag != HeapTag::Global);
  int pos = hash_and_probe(key);
  if (pos == kTooSmall) {
    reserve(len_ + 1);
    pos = hash_and_probe(key);
  }
  DCHECK(pos >= 0);

  int kv_index = index_->items_[pos];
  DCHECK(kv_index < len_);
  if (kv_index < 0) {
    // Write new entries to the end of the k/v arrays. This allows us to recall
    // insertion order until the first deletion.
    keys_->items_[len_] = key;
    values_->items_[len_] = val;
    index_->items_[pos] = len_;
    len_++;
    DCHECK(len_ <= capacity_);
  } else {
    values_->items_[kv_index] = val;
  }
}

template <typename K, typename V>
inline int len(const Dict<K, V>* d) {
  return d->len_;
}

template <class K, class V>
class DictIter {
 public:
  explicit DictIter(Dict<K, V>* D) : D_(D), pos_(0) {
  }
  void Next() {
    pos_++;
  }
  bool Done() {
    return pos_ == D_->len_;
  }
  K Key() {
    return D_->keys_->items_[pos_];
  }
  V Value() {
    return D_->values_->items_[pos_];
  }

 private:
  const Dict<K, V>* D_;
  int pos_;
};

// dict(mylist) converts a list of (k, v) tuples into a dict
template <typename K, typename V>
Dict<K, V>* dict(List<Tuple2<K, V>*>* l) {
  auto ret = Alloc<Dict<K, V>>();
  ret->reserve(len(l));
  for (ListIter<Tuple2<K, V>*> it(l); !it.Done(); it.Next()) {
    ret->set(it.Value()->at0(), it.Value()->at1());
  }
  return ret;
}

template <class K, class V>
void Dict<K, V>::update(List<Tuple2<K, V>*>* pairs) {
  reserve(len_ + len(pairs));
  for (ListIter<Tuple2<K, V>*> it(pairs); !it.Done(); it.Next()) {
    set(it.Value()->at0(), it.Value()->at1());
  }
}

template <class K, class V>
void Dict<K, V>::update(Dict<K, V>* other) {
  reserve(len_ + len(other));
  for (DictIter<K, V> it(other); !it.Done(); it.Next()) {
    set(it.Key(), it.Value());
  }
}

#endif  // MYCPP_GC_DICT_H
