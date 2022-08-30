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

#include <mycpp/gc_dict.h>
#include <mycpp/gc_dict_impl.h>

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
