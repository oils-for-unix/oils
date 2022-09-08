#ifndef LIST_TYPES_H
#define LIST_TYPES_H

#include <algorithm>  // sort() is templated

#include "mycpp/comparators.h"

class ValueError;

// Type that is layout-compatible with List (unit tests assert this).  Two
// purposes:
// - To make globals of "plain old data" at compile-time, not at startup time.
//   This can't be done with subclasses of Obj.
// - To avoid invalid-offsetof warnings when computing GC masks.

template <typename T, int N>
class GlobalList {
 public:
  OBJ_HEADER()
  int len_;
  int capacity_;
  GlobalSlab<T, N>* slab_;
};

// A list has one Slab pointer which we need to follow.
constexpr uint16_t maskof_List() {
  return maskbit(offsetof(GlobalList<int COMMA 1>, slab_));
}

template <typename T>
class List : public Obj {
  // TODO: Move methods that don't allocate or resize: out of gc_heap?
  // - allocate: append(), extend()
  // - resize: pop(), clear()
  // - neither: reverse(), sort() -- these are more like functions.  Except
  //   sort() is a templated method that depends on type param T.
  // - neither: index(), slice()

  // 8 / 4 = 2 items, or 8 / 8 = 1 item
  static const int kCapacityAdjust = kSlabHeaderSize / sizeof(T);
  static_assert(kSlabHeaderSize % sizeof(T) == 0,
                "Slab header size should be multiple of item size");

 public:
  List() : Obj(Tag::FixedSize, maskof_List(), sizeof(List<T>)) {
    // Ensured by heap zeroing.  It's never directly on the stack.
    assert(len_ == 0);
    assert(capacity_ == 0);
    assert(slab_ == nullptr);
  }

  // Implements L[i]
  T index_(int i);

  // returns index of the element
  int index(T element);

  // Implements L[i] = item
  // Note: Unlike Dict::set(), we don't need to specialize List::set() on T for
  // StackRoots because it doesn't allocate.
  void set(int i, T item);

  // L[begin:]
  List* slice(int begin);

  // L[begin:end]
  // TODO: Can this be optimized?
  List* slice(int begin, int end);

  // Should we have a separate API that doesn't return it?
  // https://stackoverflow.com/questions/12600330/pop-back-return-value
  T pop();

  // Used in osh/word_parse.py to remove from front
  // TODO: Don't accept an arbitrary index?
  T pop(int i);

  void clear();

  // Used in osh/string_ops.py
  void reverse();

  // Templated function
  void sort();

  // Ensure that there's space for a number of items
  void reserve(int n);

  // Append a single element to this list.  Must be specialized List<int> vs
  // List<Str*>.
  //
  // NOTE(Jesse): The 'must be a specialized List<int> vs List<Str*>' part of
  // the comment above is correct, however the entirety of the codebase
  // completely ignores it.  See @template_specialization_append_pointer for
  // more details and the solution.
  //
  void append(T item);

  // Extend this list with multiple elements.
  void extend(List<T>* other);

  int len_;       // number of entries
  int capacity_;  // max entries before resizing

  // The container may be resized, so this field isn't in-line.
  Slab<T>* slab_;

  DISALLOW_COPY_AND_ASSIGN(List)
};

// "Constructors" as free functions since we can't allocate within a
// constructor.  Allocation may cause garbage collection, which interferes with
// placement new.

template <typename T>
List<T>* NewList() {
  return Alloc<List<T>>();
}

// Literal ['foo', 'bar']
template <typename T>
List<T>* NewList(std::initializer_list<T> init) {
  auto self = Alloc<List<T>>();
  StackRoots _roots({&self});

  int n = init.size();
  self->reserve(n);

  int i = 0;
  for (auto item : init) {
    self->set(i, item);
    ++i;
  }
  self->len_ = n;
  return self;
}

// ['foo'] * 3
template <typename T>
List<T>* NewList(T item, int times) {
  auto self = Alloc<List<T>>();
  StackRoots _roots({&self});

  self->reserve(times);
  self->len_ = times;
  for (int i = 0; i < times; ++i) {
    self->set(i, item);
  }
  return self;
}

// e.g. List<int>
template <typename T>
void list_append(List<T>* self, T item) {
  StackRoots _roots({&self});

  self->reserve(self->len_ + 1);
  self->set(self->len_, item);
  ++self->len_;
}

// e.g. List<Str*>
template <typename T>
void list_append(List<T*>* self, T* item) {
  StackRoots _roots({&self, &item});

  self->reserve(self->len_ + 1);
  self->set(self->len_, item);
  ++self->len_;
}

template <typename T>
void List<T>::append(T item) {
  list_append(this, item);
}

template <typename T>
int len(const List<T>* L) {
  return L->len_;
}

template <typename T>
List<T>* list_repeat(T item, int times);

template <typename T>
inline bool list_contains(List<T>* haystack, T needle);

inline int int_cmp(int a, int b) {
  if (a == b) {
    return 0;
  }
  return a < b ? -1 : 1;
}

inline int str_cmp(Str* a, Str* b);
inline bool _cmp(Str* a, Str* b);

// NOTE(Jesse): Move to gc_dict_impl once I get there
template <typename K, typename V>
class Dict;

template <typename V>
List<Str*>* sorted(Dict<Str*, V>* d);

/* template <typename T> */
/* void List<T>::sort(); */

// L[begin:]
template <typename T>
List<T>* List<T>::slice(int begin) {
  if (begin < 0) {
    begin = len_ + begin;
  }

  assert(begin >= 0);

  auto self = this;
  List<T>* result = nullptr;
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
  List<T>* result = nullptr;
  StackRoots _roots({&self, &result});

  result = NewList<T>();
  for (int i = begin; i < end; i++) {
    result->append(self->slab_->items_[i]);
  }

  return result;
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
template <typename T>
int List<T>::index(T value) {
  int element_count = len(this);
  for (int i = 0; i < element_count; i++) {
    if (are_equal(slab_->items_[i], value)) {
      return i;
    }
  }
  throw Alloc<ValueError>();
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
  std::sort(slab_->items_, slab_->items_ + len_, _cmp);
}

/* template <typename T> */
/* int len(const List<T>* L) { */
/*   return L->len_; */
/* } */

// TODO: mycpp can just generate the constructor instead?
// e.g. [None] * 3
template <typename T>
List<T>* list_repeat(T item, int times) {
  return NewList<T>(item, times);
}

#if 0
template <typename T>
List<T>* NewList() {
  return Alloc<List<T>>();
}

// Literal ['foo', 'bar']
template <typename T>
List<T>* NewList(std::initializer_list<T> init) {
  auto self = Alloc<List<T>>();
  StackRoots _roots({&self});

  int n = init.size();
  self->reserve(n);

  int i = 0;
  for (auto item : init) {
    self->set(i, item);
    ++i;
  }
  self->len_ = n;
  return self;
}

// ['foo'] * 3
template <typename T>
List<T>* NewList(T item, int times) {
  auto self = Alloc<List<T>>();
  StackRoots _roots({&self});

  self->reserve(times);
  self->len_ = times;
  for (int i = 0; i < times; ++i) {
    self->set(i, item);
  }
  return self;
}
#endif

// e.g. 'a' in ['a', 'b', 'c']
template <typename T>
inline bool list_contains(List<T>* haystack, T needle) {
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

// list(L) copies the list
template <typename T>
List<T>* list(List<T>* other) {
  auto result = NewList<T>();
  for (int i = 0; i < len(other); ++i) {
    result->set(i, other->index_(i));
  }
  return result;
}

#define GLOBAL_LIST(T, N, name, array)                                      \
  GlobalSlab<T, N> _slab_##name = {Tag::Global, 0, kZeroMask, kNoObjLen,    \
                                   array};                                  \
  GlobalList<T, N> _list_##name = {Tag::Global, 0, kZeroMask,    kNoObjLen, \
                                   N,           N, &_slab_##name};          \
  List<T>* name = reinterpret_cast<List<T>*>(&_list_##name);

template <class T>
class ListIter {
 public:
  explicit ListIter(List<T>* L) : L_(L), i_(0) {
    // We need this because ListIter is directly on the stack, and L_ could be
    // moved during iteration.
    gHeap.PushRoot(reinterpret_cast<Obj**>(&L_));
  }
  ~ListIter() {
    gHeap.PopRoot();
  }
  void Next() {
    i_++;
  }
  bool Done() {
    // "unsigned size_t was a mistake"
    return i_ >= static_cast<int>(L_->len_);
  }
  T Value() {
    return L_->slab_->items_[i_];
  }

 private:
  List<T>* L_;
  int i_;
};

// TODO: Does using pointers rather than indices make this more efficient?
template <class T>
class ReverseListIter {
 public:
  explicit ReverseListIter(List<T>* L) : L_(L), i_(L_->len_ - 1) {
  }
  void Next() {
    i_--;
  }
  bool Done() {
    return i_ < 0;
  }
  T Value() {
    return L_->slab_->items_[i_];
  }

 private:
  List<T>* L_;
  int i_;
};

#endif  // LIST_TYPES_H
