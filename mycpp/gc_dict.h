#ifndef MYCPP_GC_DICT_H
#define MYCPP_GC_DICT_H

#include "mycpp/comparators.h"
#include "mycpp/gc_list.h"

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

template <class K, class V>
class Dict {
  // Relates to minimum slab size.  This is good for Dict<K*, V*>, Dict<K*,
  // int>, Dict<int, V*>, but possibly suboptimal for Dict<int, int>.  But that
  // case is rare.
  static const int kMinItems = 4;

 public:
  Dict()
      : header_(obj_header()),
        len_(0),
        capacity_(0),
        entry_(nullptr),
        keys_(nullptr),
        values_(nullptr) {
  }

  Dict(std::initializer_list<K> keys, std::initializer_list<V> values)
      : header_(obj_header()),
        len_(0),
        capacity_(0),
        entry_(nullptr),
        keys_(nullptr),
        values_(nullptr) {
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
  void set(K key, V val);

  void update(List<Tuple2<K, V>*>* kvs);

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

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(Dict));
  }

  GC_OBJ(header_);
  int len_;       // number of entries (keys and values, almost dense)
  int capacity_;  // number of entries before resizing

  // These 3 slabs are resized at the same time.
  Slab<int>* entry_;  // NOW: kEmptyEntry, kDeletedEntry, or 0.
                      // LATER: indices which are themselves indexed by // hash
                      // value % capacity_
  Slab<K>* keys_;     // Dict<int, V>
  Slab<V>* values_;   // Dict<K, int>

  // A dict has 3 pointers the GC needs to follow.
  static constexpr uint16_t field_mask() {
    return maskbit(offsetof(Dict, entry_)) | maskbit(offsetof(Dict, keys_)) |
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
inline bool dict_contains(Dict<K, V>* haystack, K needle) {
  return haystack->position_of_key(needle) != -1;
}

// TODO: Remove one of these styles using mycpp code gen
template <typename K, typename V>
Dict<K, V>* NewDict() {
  return Alloc<Dict<K, V>>();
}

template <typename K, typename V>
Dict<K, V>* NewDict(std::initializer_list<K> keys,
                    std::initializer_list<V> values) {
  assert(keys.size() == values.size());
  auto self = Alloc<Dict<K, V>>();
  auto v = values.begin();  // This simulates a "zip" loop
  for (auto key : keys) {
    self->set(key, *v);
    ++v;
  }

  return self;
}

template <typename K, typename V>
void Dict<K, V>::reserve(int n) {
  Slab<int>* new_i = nullptr;
  Slab<K>* new_k = nullptr;
  Slab<V>* new_v = nullptr;
  // log("--- reserve %d", capacity_);
  //
  if (capacity_ < n) {  // TODO: use load factor, not exact fit
    // calculate the number of keys and values we should have
    capacity_ = RoundCapacity(n + kCapacityAdjust) - kCapacityAdjust;

    // TODO: This is SPARSE.  How to compute a size that ensures a decent
    // load factor?
    int index_len = capacity_;
    new_i = NewSlab<int>(index_len);

    // For the linear search to work
    for (int i = 0; i < index_len; ++i) {
      new_i->items_[i] = kEmptyEntry;
    }

    // These are DENSE.
    new_k = NewSlab<K>(capacity_);
    new_v = NewSlab<V>(capacity_);

    if (keys_ != nullptr) {
      // Right now the index is the same size as keys and values.
      memcpy(new_i->items_, entry_->items_, len_ * sizeof(int));

      memcpy(new_k->items_, keys_->items_, len_ * sizeof(K));
      memcpy(new_v->items_, values_->items_, len_ * sizeof(V));
    }

    entry_ = new_i;
    keys_ = new_k;
    values_ = new_v;
  }
}

// d[key] in Python: raises KeyError if not found
template <typename K, typename V>
V Dict<K, V>::index_(K key) {
  int pos = position_of_key(key);
  if (pos == -1) {
    throw Alloc<KeyError>();
  } else {
    return values_->items_[pos];
  }
}

// Get a key.
// Returns nullptr if not found (Can't use this for non-pointer types?)
template <typename K, typename V>
V Dict<K, V>::get(K key) {
  int pos = position_of_key(key);
  if (pos == -1) {
    return nullptr;
  } else {
    return values_->items_[pos];
  }
}

// Get a key, but return a default if not found.
// expr_parse.py uses this with OTHER_BALANCE
template <typename K, typename V>
V Dict<K, V>::get(K key, V default_val) {
  int pos = position_of_key(key);
  if (pos == -1) {
    return default_val;
  } else {
    return values_->items_[pos];
  }
}

template <typename K, typename V>
List<K>* Dict<K, V>::keys() {
  return ListFromDictSlab<K>(entry_, keys_, capacity_);
}

// For AssocArray transformations
template <typename K, typename V>
List<V>* Dict<K, V>::values() {
  return ListFromDictSlab<V>(entry_, values_, capacity_);
}

template <typename K, typename V>
void Dict<K, V>::clear() {
  // Maintain invariant
  for (int i = 0; i < capacity_; ++i) {
    entry_->items_[i] = kEmptyEntry;
  }

  memset(keys_->items_, 0, len_ * sizeof(K));    // zero for GC scan
  memset(values_->items_, 0, len_ * sizeof(V));  // zero for GC scan
  len_ = 0;
}

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
template <typename K, typename V>
int Dict<K, V>::position_of_key(K key) {
  for (int i = 0; i < capacity_; ++i) {
    int special = entry_->items_[i];  // NOT an index now
    if (special == kDeletedEntry) {
      continue;  // keep searching
    }
    if (special == kEmptyEntry) {
      return -1;  // not found
    }
    if (keys_equal(keys_->items_[i], key)) {
      return i;
    }
  }
  return -1;  // table is completely full?  Does this happen?
}

template <typename K, typename V>
void Dict<K, V>::set(K key, V val) {
  int pos = position_of_key(key);
  if (pos == -1) {  // new pair
    reserve(len_ + 1);
    keys_->items_[len_] = key;
    values_->items_[len_] = val;

    entry_->items_[len_] = 0;  // new special value

    ++len_;
  } else {
    values_->items_[pos] = val;
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
  explicit DictIter(Dict<K, V>* D) : D_(D), pos_(ValidPosAfter(0)) {
  }
  void Next() {
    pos_ = ValidPosAfter(pos_ + 1);
  }
  bool Done() {
    return pos_ == -1;
  }
  K Key() {
    return D_->keys_->items_[pos_];
  }
  V Value() {
    return D_->values_->items_[pos_];
  }

 private:
  int ValidPosAfter(int pos) {
    // Returns the position of a valid entry at or after index i_.  Or -1 if
    // there isn't one.  Advances i_ too.
    while (true) {
      if (pos >= D_->capacity_) {
        return -1;
      }
      int index = D_->entry_->items_[pos];
      if (index == kDeletedEntry) {
        ++pos;
        continue;  // increment again
      }
      if (index == kEmptyEntry) {
        return -1;
      }
      break;
    }
    return pos;
  }

  Dict<K, V>* D_;
  int pos_;
};

// dict(l) converts a list of (k, v) tuples into a dict
template <typename K, typename V>
Dict<K, V>* dict(List<Tuple2<K, V>*>* l) {
  auto ret = NewDict<K, V>();
  ret->reserve(len(l));
  for (ListIter<Tuple2<K, V>*> it(l); !it.Done(); it.Next()) {
    ret->set(it.Value()->at0(), it.Value()->at1());
  }
  return ret;
}

#endif  // MYCPP_GC_DICT_H
