#ifndef MYCPP_GC_DICT_H
#define MYCPP_GC_DICT_H

#include "mycpp/comparators.h"
#include "mycpp/gc_builtins.h"
#include "mycpp/gc_list.h"
#include "mycpp/hash.h"

// Non-negative entries in index_ are array indices into keys_ and values_.
// There are two special negative entries.

// index that means this Dict item was deleted (a tombstone).
const int kDeletedEntry = -1;

// index that means this Dict entry is free.  Because we have Dict[int, int],
// we can't use a sentinel entry in keys_.  It has to be a sentinel entry in
// index_.
const int kEmptyEntry = -2;

// NOTE: This is just a return value. It is never stored in the index.
const int kNotFound = -3;

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
  // Relates to minimum slab size.  This is good for Dict<K*, V*>, Dict<K*,
  // int>, Dict<int, V*>, but possibly suboptimal for Dict<int, int>.  But that
  // case is rare.
  static const int kMinItems = 4;

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
    assert(keys.size() == values.size());
    auto v = values.begin();  // This simulates a "zip" loop
    for (auto key : keys) {
      // note: calls reserve(), and maybe allocate
      this->set(key, *v);
      ++v;
    }
  }

  // This relies on the fact that containers of 4-byte ints are reduced by 2
  // items, which is greater than (or equal to) the reduction of any other
  // type
  static const int kCapacityAdjust = kSlabHeaderSize / sizeof(int);
  static_assert(kSlabHeaderSize % sizeof(int) == 0,
                "Slab header size should be multiple of key size");

  // Reserve enough space in the index and table for at least `new_size`
  // entries.
  void reserve(int new_size);

  // d[key] in Python: raises KeyError if not found
  V at(K key) const;

  // Get a key.
  // Returns nullptr if not found (Can't use this for non-pointer types?)
  V get(K key) const;

  // Get a key, but return a default if not found.
  // expr_parse.py uses this with OTHER_BALANCE
  V get(K key, V default_val) const;

  // Implements d[k] = v.  May resize the dictionary.
  void set(K key, V val);

  void update(List<Tuple2<K, V>*>* kvs);

  List<K>* keys() const;

  // For AssocArray transformations
  List<V>* values() const;

  void clear();

  // Returns an offset into the index for given key. If the key is not already
  // in the table and there is room, the offset to an empty slot will be
  // returned. The caller is responsible for checking if the index slot is empty
  // before using it.
  //
  // Returns kNotFound if the dictionary is full. The caller can use this as a
  // cue to grow the table.
  //
  // Used by dict_contains(), index(), get(), and set().
  int hash_and_probe(K key) const;

  // Returns an offset into the table (keys_/values_) for the given key.
  //
  // Returns kNotFound if the key isn't in the table.
  int find_kv_index(K key) const;

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(Dict));
  }

  int len_;        // number of entries (keys and values, almost dense)
  int capacity_;   // number of k/v slots
  int index_len_;  // number of index slots

  // These 3 slabs are resized at the same time.
  Slab<int>* index_;  // kEmptyEntry, kDeletedEntry, or a valid index into
                      // keys_/values_
  Slab<K>* keys_;     // Dict<int, V>
  Slab<V>* values_;   // Dict<K, int>

  // A dict has 3 pointers the GC needs to follow.
  static constexpr uint32_t field_mask() {
    return maskbit(offsetof(Dict, index_)) | maskbit(offsetof(Dict, keys_)) |
           maskbit(offsetof(Dict, values_));
  }

  DISALLOW_COPY_AND_ASSIGN(Dict)

 private:
  int RoundCapacity(int n) {
    if (n < kMinItems) {
      return kMinItems;
    }
    return RoundUp(n);
  }
};

template <typename K, typename V>
inline bool dict_contains(const Dict<K, V>* haystack, K needle) {
  int pos = haystack->hash_and_probe(needle);
  return pos != kNotFound && haystack->index_->items_[pos] >= 0;
}

template <typename K, typename V>
void Dict<K, V>::reserve(int new_size) {
  Slab<int>* new_i = nullptr;
  Slab<K>* new_k = nullptr;
  Slab<V>* new_v = nullptr;
  Slab<K>* old_k = keys_;
  Slab<V>* old_v = values_;
  int old_len = len_;
  // log("--- reserve %d", capacity_);
  //
  if (capacity_ < new_size) {
    // calculate the number of keys and values we should have
    capacity_ = RoundCapacity(new_size + kCapacityAdjust) - kCapacityAdjust;

    // capacity_ is rounded to a power of two, so this division should be safe.
    index_len_ = 3 * (capacity_ / 2);
    DCHECK(index_len_ > capacity_);
    new_i = NewSlab<int>(index_len_);
    for (int i = 0; i < index_len_; ++i) {
      new_i->items_[i] = kEmptyEntry;
    }

    // These are DENSE.
    new_k = NewSlab<K>(capacity_);
    new_v = NewSlab<V>(capacity_);

    index_ = new_i;
    keys_ = new_k;
    values_ = new_v;
    len_ = 0;

    if (old_k != nullptr) {
      // rehash
      for (int i = 0; i < old_len; ++i) {
        set(old_k->items_[i], old_v->items_[i]);
      }
    }
  }
}

// d[key] in Python: raises KeyError if not found
template <typename K, typename V>
V Dict<K, V>::at(K key) const {
  int kv_index = find_kv_index(key);
  if (kv_index == kNotFound) {
    throw Alloc<KeyError>();
  } else {
    return values_->items_[kv_index];
  }
}

// Get a key.
// Returns nullptr if not found (Can't use this for non-pointer types?)
template <typename K, typename V>
V Dict<K, V>::get(K key) const {
  int kv_index = find_kv_index(key);
  if (kv_index == kNotFound) {
    return nullptr;
  } else {
    return values_->items_[kv_index];
  }
}

// Get a key, but return a default if not found.
// expr_parse.py uses this with OTHER_BALANCE
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

// For AssocArray transformations
template <typename K, typename V>
List<V>* Dict<K, V>::values() const {
  return ListFromDictSlab<V>(values_, len_);
}

template <typename K, typename V>
void Dict<K, V>::clear() {
  // Maintain invariant
  for (int i = 0; i < capacity_; ++i) {
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
// - Special case to intern Str* when it's hashed?  How?
//   - Should we have wrappers like:
//   - V GetAndIntern<V>(D, &string_key)
//   - SetAndIntern<V>(D, &string_key, value)
//   This will enable duplicate copies of the string to be garbage collected
template <typename K, typename V>
int Dict<K, V>::hash_and_probe(K key) const {
  if (capacity_ == 0) {
    return kNotFound;
  }

  // Hash the key onto a slot in the index. If the first slot is occupied, probe
  // until an empty one is found.
  unsigned h = hash_key(key);
  int init_bucket = h % index_len_;

  // If we see a tombstone along the probing path, stash it.
  int open_slot = -1;

  for (int i = 0; i < index_len_; ++i) {
    // Start at init_bucket and wrap araound
    // NOTE: if division becomes a hotspot, split this into two loops.
    int slot = (i + init_bucket) % index_len_;

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
      return len_ < capacity_ ? slot : kNotFound;
    }

    // Tombstone or collided keys unequal. Keep scanning.
    DCHECK(kv_index >= 0 || kv_index == kDeletedEntry);
    if (kv_index == kDeletedEntry && open_slot == -1) {
      // NOTE: We only record the open slot here. We DON'T return it. If we're
      // looking for a key that was deleted before this tombstone was written to
      // the index we should continue probing until we get to that key. If we
      // get to an empty index slot or the end of the index then we know we are
      // dealing with a new key and can safely replace the tombstone without
      // disrupting any existing keys.
      open_slot = slot;
    }
  }

  if (open_slot >= 0) {
    return open_slot;
  }
  return kNotFound;
}

template <typename K, typename V>
int Dict<K, V>::find_kv_index(K key) const {
  if (index_ != nullptr) {
    // Common case.
    int pos = hash_and_probe(key);
    if (pos == kNotFound || index_->items_[pos] < 0) {
      return kNotFound;
    }
    return index_->items_[pos];
  }

  // GlobalDict. Just scan.
  for (int i = 0; i < len_; ++i) {
    if (keys_equal(keys_->items_[i], key)) {
      return i;
    }
  }

  // Not found.
  return kNotFound;
}

template <typename K, typename V>
void Dict<K, V>::set(K key, V val) {
  DCHECK(obj_header().heap_tag != HeapTag::Global);
  int pos = hash_and_probe(key);
  if (pos == kNotFound) {
    reserve(len_ + 1);
    pos = hash_and_probe(key);
  }
  DCHECK(pos >= 0);
  int kv_index = index_->items_[pos];
  DCHECK(kv_index < len_);
  if (kv_index < 0) {
    // Always write new entries to the end of the k/v arrays. This allows us to
    // recall the insertion order of keys trivially in most cases.
    keys_->items_[len_] = key;
    values_->items_[len_] = val;
    index_->items_[pos] = len_;
    len_++;
  } else {
    values_->items_[kv_index] = val;
  }
}

template <class K, class V>
void Dict<K, V>::update(List<Tuple2<K, V>*>* kvs) {
  for (ListIter<Tuple2<K, V>*> it(kvs); !it.Done(); it.Next()) {
    set(it.Value()->at0(), it.Value()->at1());
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

// dict(l) converts a list of (k, v) tuples into a dict
template <typename K, typename V>
Dict<K, V>* dict(List<Tuple2<K, V>*>* l) {
  auto ret = Alloc<Dict<K, V>>();
  ret->reserve(len(l));
  for (ListIter<Tuple2<K, V>*> it(l); !it.Done(); it.Next()) {
    ret->set(it.Value()->at0(), it.Value()->at1());
  }
  return ret;
}

#endif  // MYCPP_GC_DICT_H
