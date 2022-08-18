// mycpp/gc_containers.h
//
// Definitions of Str, List<T>, Dict<K, V>, and related functions.

#ifndef GC_TYPES_H
#define GC_TYPES_H

#ifdef OLDSTL_BINDINGS
  #error \
      "This file contains definitions for gc'd containers and should not be included in leaky builds!  Include oldstl_containers.h instead."
#endif

#include "mycpp/gc_heap.h"
#include "mycpp/gc_str.h"
#include "mycpp/comparators.h"

extern Str* kEmptyString;

#include "mycpp/gc_slab.h"

template <int N>
class GlobalStr {
  // A template type with the same layout as Str with length N-1 (which needs a
  // buffer of size N).  For initializing global constant instances.
 public:
  OBJ_HEADER()

  int hash_value_;
  const char data_[N];

  DISALLOW_COPY_AND_ASSIGN(GlobalStr)
};

// This macro is a workaround for the fact that it's impossible to have a
// a constexpr initializer for char[N].  The "String Literals as Non-Type
// Template Parameters" feature of C++ 20 would have done it, but it's not
// there.
//
// https://old.reddit.com/r/cpp_questions/comments/j0khh6/how_to_constexpr_initialize_class_member_thats/
// https://stackoverflow.com/questions/10422487/how-can-i-initialize-char-arrays-in-a-constructor

#define GLOBAL_STR(name, val)                                            \
  GlobalStr<sizeof(val)> _##name = {                                     \
      Tag::Global, 0, kZeroMask, kStrHeaderSize + sizeof(val), -1, val}; \
  Str* name = reinterpret_cast<Str*>(&_##name);

//
// List<T>
//

#define GLOBAL_LIST(T, N, name, array)                                      \
  GlobalSlab<T, N> _slab_##name = {Tag::Global, 0, kZeroMask, kNoObjLen,    \
                                   array};                                  \
  GlobalList<T, N> _list_##name = {Tag::Global, 0, kZeroMask,    kNoObjLen, \
                                   N,           N, &_slab_##name};          \
  List<T>* name = reinterpret_cast<List<T>*>(&_list_##name);

#include "mycpp/gc_list.h"

//
// Dict<K, V>
//

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

  // This relies on the fact that containers of 4-byte ints are reduced by 2
  // items, which is greater than (or equal to) the reduction of any other
  // type
  static const int kCapacityAdjust = kSlabHeaderSize / sizeof(int);
  static_assert(kSlabHeaderSize % sizeof(int) == 0,
                "Slab header size should be multiple of key size");

  void reserve(int n) {
    auto self = this;
    Slab<int>* new_i = nullptr;
    Slab<K>* new_k = nullptr;
    Slab<V>* new_v = nullptr;
    StackRoots _roots({&self, &new_i, &new_k, &new_v});

    // log("--- reserve %d", capacity_);
    //
    if (self->capacity_ < n) {  // TODO: use load factor, not exact fit
      // calculate the number of keys and values we should have
      self->capacity_ = RoundUp(n + kCapacityAdjust) - kCapacityAdjust;

      // TODO: This is SPARSE.  How to compute a size that ensures a decent
      // load factor?
      int index_len = self->capacity_;
      new_i = NewSlab<int>(index_len);

      // For the linear search to work
      for (int i = 0; i < index_len; ++i) {
        new_i->items_[i] = kEmptyEntry;
      }

      // These are DENSE.
      new_k = NewSlab<K>(self->capacity_);
      new_v = NewSlab<V>(self->capacity_);

      if (self->keys_ != nullptr) {
        // Right now the index is the same size as keys and values.
        memcpy(new_i->items_, self->entry_->items_, self->len_ * sizeof(int));

        memcpy(new_k->items_, self->keys_->items_, self->len_ * sizeof(K));
        memcpy(new_v->items_, self->values_->items_, self->len_ * sizeof(V));
      }

      self->entry_ = new_i;
      self->keys_ = new_k;
      self->values_ = new_v;
    }
  }

  // d[key] in Python: raises KeyError if not found
  V index_(K key) {
    int pos = position_of_key(key);
    if (pos == -1) {
      InvalidCodePath();  // NOTE(Jesse): Should we really crash if asking for a
                          // key not in a dict?
    } else {
      return values_->items_[pos];
    }
  }

  // Get a key.
  // Returns nullptr if not found (Can't use this for non-pointer types?)
  V get(K key) {
    int pos = position_of_key(key);
    if (pos == -1) {
      return nullptr;
    } else {
      return values_->items_[pos];
    }
  }

  // Get a key, but return a default if not found.
  // expr_parse.py uses this with OTHER_BALANCE
  V get(K key, V default_val) {
    int pos = position_of_key(key);
    if (pos == -1) {
      return default_val;
    } else {
      return values_->items_[pos];
    }
  }

  // Implements d[k] = v.  May resize the dictionary.
  //
  // TODO: Need to specialize this for StackRoots!  Gah!
  void set(K key, V val);

  List<K>* keys() {
    return ListFromDictSlab<K>(entry_, keys_, capacity_);
  }

  // For AssocArray transformations
  List<V>* values() {
    return ListFromDictSlab<V>(entry_, values_, capacity_);
  }

  void clear() {
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
  int position_of_key(K key) {
    auto self = this;
    StackRoots _roots({&self});

    for (int i = 0; i < self->capacity_; ++i) {
      int special = self->entry_->items_[i];  // NOT an index now
      if (special == kDeletedEntry) {
        continue;  // keep searching
      }
      if (special == kEmptyEntry) {
        return -1;  // not found
      }
      if (keys_equal(self->keys_->items_[i], key)) {
        return i;
      }
    }
    return -1;  // table is completely full?  Does this happen?
  }

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

// "Constructors" that allocate

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

// Four overloads for dict_set()!  TODO: Is there a nicer way to do this?

// e.g. Dict<int, int>
template <typename K, typename V>
void dict_set(Dict<K, V>* self, K key, V val) {
  StackRoots _roots({&self});

  self->reserve(self->len_ + 1);
  self->keys_->items_[self->len_] = key;
  self->values_->items_[self->len_] = val;

  self->entry_->items_[self->len_] = 0;  // new special value

  ++self->len_;
}

// e.g. Dict<Str*, int>
template <typename K, typename V>
void dict_set(Dict<K*, V>* self, K* key, V val) {
  StackRoots _roots({&self, &key});

  self->reserve(self->len_ + 1);
  self->keys_->items_[self->len_] = key;
  self->values_->items_[self->len_] = val;

  self->entry_->items_[self->len_] = 0;  // new special value

  ++self->len_;
}

// e.g. Dict<int, Str*>
template <typename K, typename V>
void dict_set(Dict<K, V*>* self, K key, V* val) {
  StackRoots _roots({&self, &val});

  self->reserve(self->len_ + 1);
  self->keys_->items_[self->len_] = key;
  self->values_->items_[self->len_] = val;

  self->entry_->items_[self->len_] = 0;  // new special value

  ++self->len_;
}

// e.g. Dict<Str*, Str*>
template <typename K, typename V>
void dict_set(Dict<K*, V*>* self, K* key, V* val) {
  StackRoots _roots({&self, &key, &val});

  self->reserve(self->len_ + 1);
  self->keys_->items_[self->len_] = key;
  self->values_->items_[self->len_] = val;

  self->entry_->items_[self->len_] = 0;  // new special value

  ++self->len_;
}

template <typename K, typename V>
void Dict<K, V>::set(K key, V val) {
  auto self = this;
  StackRoots _roots({&self});  // May not need this here?

  int pos = self->position_of_key(key);
  if (pos == -1) {             // new pair
    dict_set(self, key, val);  // ALLOCATES
  } else {
    self->values_->items_[pos] = val;
  }
}

template <typename K, typename V>
inline int len(const Dict<K, V>* d) {
  return d->len_;
}

#endif  // GC_TYPES_H
