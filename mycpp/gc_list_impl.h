#ifndef LIST_IMPL_H
#define LIST_IMPL_H

#include "mycpp/error_types.h"

bool are_equal(Tuple2<Str*, int>* t1, Tuple2<Str*, int>* t2);
bool are_equal(int, int);

  // Implements L[i]
template <typename T>
T List<T>::index_(int i) {

  if (i < 0) {
    int j = len_ + i;
    assert(j < len_);
    assert(j >= 0);
    return slab_->items_[j];
  }

  assert(i < len_);
  assert(i >= 0);
  return slab_->items_[i];
}


// L.index(i) -- Python method
template<typename T>
int List<T>::index(T value) {
  int element_count = len(this);
  for (int i = 0; i < element_count ; i++) {
    if (are_equal(slab_->items_[i], value)) {
      return i;
    }
  }
  throw new ValueError();
}



// Implements L[i] = item
// Note: Unlike Dict::set(), we don't need to specialize List::set() on T for
// StackRoots because it doesn't allocate.
template <typename T>
void List<T>::set(int i, T item) {
  if (i < 0) {
    i = len_ + i;
  }

  assert(i >= 0);
  assert(i < capacity_);

  slab_->items_[i] = item;
}

// L[begin:]
template <typename T>
List<T>* List<T>::slice(int begin) {

  if (begin < 0) {
    begin = len_ + begin;
  }

  assert(begin >= 0);

  auto self = this;
  List<T> *result = nullptr;
  StackRoots _roots({&self, &result});

  result = NewList<T>();

  for (int i = begin; i < self->len_; i++) {
    result->append(self->slab_->items_[i]);
  }

  return result;
}

// L[begin:end]
// TODO: Can this be optimized?
template <typename T>
List<T>* List<T>::slice(int begin, int end) {

  if (begin < 0) {
    begin = len_ + begin;
  }
  if (end < 0) {
    end = len_ + end;
  }

  assert(end <= len_);
  assert(begin >= 0);
  assert(end >= 0);

  auto self = this;
  List<T> *result = nullptr;
  StackRoots _roots({&self, &result});

  result = NewList<T>();
  for (int i = begin; i < end; i++) {
    result->append(self->slab_->items_[i]);
  }

  return result;
}

  // Should we have a separate API that doesn't return it?
  // https://stackoverflow.com/questions/12600330/pop-back-return-value
template <typename T>
T List<T>::pop() {
  assert(len_ > 0);
  len_--;
  T result = slab_->items_[len_];
  slab_->items_[len_] = 0;  // zero for GC scan
  return result;
}

// Used in osh/word_parse.py to remove from front
// TODO: Don't accept an arbitrary index?
//
// NOTE(Jesse): This operation is typically called 'shift' I think
template <typename T>
T List<T>::pop(int i) {
  assert(len_ > 0);
  assert(i == 0);  // only support popping the first item

  T result = index_(0);
  len_--;

  // Shift everything by one
  memmove(slab_->items_, slab_->items_ + 1, len_ * sizeof(T));

  /*
  for (int j = 0; j < len_; j++) {
    slab_->items_[j] = slab_->items_[j+1];
  }
  */

  slab_->items_[len_] = 0;  // zero for GC scan
  return result;
}

template <typename T>
void List<T>::clear() {
  memset(slab_->items_, 0, len_ * sizeof(T));  // zero for GC scan
  len_ = 0;
}

  // Used in osh/string_ops.py
template <typename T>
void List<T>::reverse() {
  for (int i = 0; i < len_ / 2; ++i) {
    // log("swapping %d and %d", i, n-i);
    T tmp = slab_->items_[i];
    int j = len_ - 1 - i;
    slab_->items_[i] = slab_->items_[j];
    slab_->items_[j] = tmp;
  }
}

  // Ensure that there's space for a number of items
template <typename T>
void List<T>::reserve(int n) {
  // log("reserve capacity = %d, n = %d", capacity_, n);
  auto self = this;
  StackRoots _roots({&self});

  // Don't do anything if there's already enough space.
  if (self->capacity_ >= n) return;

  // Example: The user asks for space for 7 integers.  Account for the
  // header, and say we need 9 to determine the obj length.  9 is
  // rounded up to 16, for a 64-byte obj.  Then we actually have space
  // for 14 items.
  self->capacity_ = RoundUp(n + kCapacityAdjust) - kCapacityAdjust;
  auto new_slab = NewSlab<T>(self->capacity_);

  if (self->len_ > 0) {
    // log("Copying %d bytes", len_ * sizeof(T));
    memcpy(new_slab->items_, self->slab_->items_, self->len_ * sizeof(T));
  }
  self->slab_ = new_slab;
}

  // Extend this list with multiple elements.
template <typename T>
void List<T>::extend(List<T>* other) {
  auto self = this;
  StackRoots _roots({&self, &other});

  int n = other->len_;
  int new_len = self->len_ + n;
  self->reserve(new_len);

  for (int i = 0; i < n; ++i) {
    self->set(self->len_ + i, other->slab_->items_[i]);
  }
  self->len_ = new_len;
}

#include <algorithm>

inline int int_cmp(int a, int b) {
  if (a == b) {
    return 0;
  }
  return a < b ? -1 : 1;
}

// NOTE(Jesse): It's highly sus that we have str_equals and str_cmp..
// shouldn't we write one in terms of the other?
//
// @duplicate_string_compare_code
//
// Used by [[ a > b ]] and so forth
inline int str_cmp(Str* a, Str* b) {
  int len_a = len(a);
  int len_b = len(b);

  int min = std::min(len_a, len_b);
  if (min == 0) {
    return int_cmp(len_a, len_b);
  }
  int comp = memcmp(a->data_, b->data_, min);
  if (comp == 0) {
    return int_cmp(len_a, len_b);  // tiebreaker
  }
  return comp;
}

inline bool _cmp(Str* a, Str* b) {
  return str_cmp(a, b) < 0;
}

template <typename T>
void List<T>::sort() {
  std::sort( (Str**)slab_->items_, slab_->items_ + len_, _cmp);
}

template <typename T>
int len(const List<T>* L) {
  return L->len_;
}

// TODO: mycpp can just generate the constructor instead?
// e.g. [None] * 3
template <typename T>
List<T>* list_repeat(T item, int times) {
  return NewList<T>(item, times);
}

namespace id_kind_asdl {
enum class Kind;
};

// NOTE(Jesse): Where should this _actually_ go?  Definitely not here.
inline bool are_equal(id_kind_asdl::Kind left, id_kind_asdl::Kind right);
bool are_equal(int left, int right);

// e.g. 'a' in ['a', 'b', 'c']
template <typename T>
inline bool list_contains(List<T> *haystack, T needle) {
  // StackRoots _roots({&haystack, &needle});  // doesn't allocate

  int n = len(haystack);
  for (int i = 0; i < n; ++i) {
    if (are_equal(haystack->index_(i), needle)) {
      return true;
    }
  }
  return false;
}

// NOTE(Jesse): Move to gc_dict_impl once I get there
template <typename K, typename V>
class Dict;

template <typename V>
List<Str*>* sorted(Dict<Str*, V>* d) {
  auto keys = d->keys();
  keys->sort();
  return keys;
}


#endif // LIST_IMPL_H
