#ifndef MYCPP_GC_LIST_H
#define MYCPP_GC_LIST_H

#include <string.h>  // memcpy

#include <algorithm>  // sort() is templated

#include "mycpp/common.h"  // DCHECK
#include "mycpp/comparators.h"
#include "mycpp/gc_alloc.h"     // Alloc
#include "mycpp/gc_builtins.h"  // ValueError
#include "mycpp/gc_slab.h"

// GlobalList layout-compatible with List (unit tests assert this), and it can
// be a true C global (incurs zero startup time)

template <typename T, int N>
class GlobalList {
 public:
  int len_;
  int capacity_;
  GlobalSlab<T, N>* slab_;
};

template <typename T>
class List {
  // Relate slab size to number of items (capacity)
  // 8 / 4 = 2 items, or 8 / 8 = 1 item
  static const int kCapacityAdjust = kSlabHeaderSize / sizeof(T);
  static_assert(kSlabHeaderSize % sizeof(T) == 0,
                "Slab header size should be multiple of item size");

  // Relates to minimum Slab size.
  // Smallest non-empty List<T*>  should have about 4 items, or 3 without header
  // Smallest non-empty List<int> should have about 8 items, or 7 without header
  static const int kMinItems = 32 / sizeof(T);
  static_assert(32 % sizeof(T) == 0,
                "An integral number of items should fit in 32 bytes");

 public:
  List() : len_(0), capacity_(0), slab_(nullptr) {
  }

  // Implements L[i]
  T index_(int i);

  // returns index of the element
  int index(T element);

  // Implements L[i] = item
  void set(int i, T item);

  // L[begin:]
  List* slice(int begin);

  // L[begin:end]
  List* slice(int begin, int end);

  // L[begin:end:step]
  List* slice(int begin, int end, int step);

  // Should we have a separate API that doesn't return it?
  // https://stackoverflow.com/questions/12600330/pop-back-return-value
  T pop();

  // Used in osh/word_parse.py to remove from front
  T pop(int i);

  // Remove the first occourence of x from the list.
  void remove(T x);

  void clear();

  // Used in osh/string_ops.py
  void reverse();

  // Templated function
  void sort();

  // Ensure that there's space for a number of items
  void reserve(int n);

  // Append a single element to this list.
  void append(T item);

  // Extend this list with multiple elements.
  void extend(List<T>* other);

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(List<T>));
  }

  int len_;       // number of entries
  int capacity_;  // max entries before resizing

  // The container may be resized, so this field isn't in-line.
  Slab<T>* slab_;

  // A list has one Slab pointer which we need to follow.
  static constexpr uint32_t field_mask() {
    return maskbit(offsetof(List, slab_));
  }

  DISALLOW_COPY_AND_ASSIGN(List)

 private:
  int RoundCapacity(int n) {
    if (n < kMinItems) {
      return kMinItems;
    }
    return RoundUp(n);
  }
};

// "Constructors" as free functions since we can't allocate within a
// constructor.  Allocation may cause garbage collection, which interferes with
// placement new.

// This is not really necessary, only syntactic sugar.
template <typename T>
List<T>* NewList() {
  return Alloc<List<T>>();
}

// Literal ['foo', 'bar']
// This seems to allow better template argument type deduction than a
// constructor.
template <typename T>
List<T>* NewList(std::initializer_list<T> init) {
  auto self = Alloc<List<T>>();

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

  self->reserve(times);
  self->len_ = times;
  for (int i = 0; i < times; ++i) {
    self->set(i, item);
  }
  return self;
}

template <typename T>
void List<T>::append(T item) {
  reserve(len_ + 1);
  slab_->items_[len_] = item;
  ++len_;
}

template <typename T>
int len(const List<T>* L) {
  return L->len_;
}

template <typename T>
List<T>* list_repeat(T item, int times);

template <typename T>
inline bool list_contains(List<T>* haystack, T needle);

template <typename K, typename V>
class Dict;  // forward decl

template <typename V>
List<Str*>* sorted(Dict<Str*, V>* d);

template <typename T>
List<T>* sorted(List<T>* l);

// L[begin:]
// TODO: Implement this in terms of slice(begin, end)
template <typename T>
List<T>* List<T>::slice(int begin) {
  if (begin < 0) {
    begin = len_ + begin;
  }

  DCHECK(begin >= 0);

  List<T>* result = nullptr;
  result = NewList<T>();

  for (int i = begin; i < len_; i++) {
    result->append(slab_->items_[i]);
  }

  return result;
}

// L[begin:end]
template <typename T>
List<T>* List<T>::slice(int begin, int end) {
  return slice(begin, end, 1);
}

// L[begin:end:step]
template <typename T>
List<T>* List<T>::slice(int begin, int end, int step) {
  if (begin < 0) {
    begin = len_ + begin;
  }
  if (end < 0) {
    end = len_ + end;
  }

  DCHECK(end <= len_);
  DCHECK(begin >= 0);
  DCHECK(end >= 0);

  List<T>* result = NewList<T>();
  // step might be negative
  for (int i = begin; begin <= i && i < end; i += step) {
    result->append(slab_->items_[i]);
  }

  return result;
}

// Ensure that there's space for a number of items
template <typename T>
void List<T>::reserve(int n) {
  // log("reserve capacity = %d, n = %d", capacity_, n);

  // Don't do anything if there's already enough space.
  if (capacity_ >= n) {
    return;
  }

  // Slabs should be a total of 2^N bytes.  kCapacityAdjust is the number of
  // items that the 8 byte header takes up: 1 for List<T*>, and 2 for
  // List<int>.
  //
  // Example: the user reserves space for 3 integers.  The minimum number of
  // items would be 5, which is rounded up to 8.  Subtract 2 again, giving 6,
  // which leads to 8 + 6*4 = 32 byte Slab.

  capacity_ = RoundCapacity(n + kCapacityAdjust) - kCapacityAdjust;
  auto new_slab = NewSlab<T>(capacity_);

  if (len_ > 0) {
    // log("Copying %d bytes", len_ * sizeof(T));
    memcpy(new_slab->items_, slab_->items_, len_ * sizeof(T));
  }
  slab_ = new_slab;
}

// Implements L[i] = item
template <typename T>
void List<T>::set(int i, T item) {
  if (i < 0) {
    i = len_ + i;
  }

  DCHECK(i >= 0);
  DCHECK(i < capacity_);

  slab_->items_[i] = item;
}

// Implements L[i]
template <typename T>
T List<T>::index_(int i) {
  if (i < 0) {
    int j = len_ + i;
    if (j >= len_ || j < 0) {
      throw Alloc<IndexError>();
    }
    return slab_->items_[j];
  }

  if (i >= len_ || i < 0) {
    throw Alloc<IndexError>();
  }
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
  if (len_ == 0) {
    throw Alloc<IndexError>();
  }
  len_--;
  T result = slab_->items_[len_];
  slab_->items_[len_] = 0;  // zero for GC scan
  return result;
}

// Used in osh/word_parse.py to remove from front
template <typename T>
T List<T>::pop(int i) {
  if (len_ < i) {
    throw Alloc<IndexError>();
  }

  T result = index_(i);
  len_--;

  // Shift everything by one
  memmove(slab_->items_ + i, slab_->items_ + (i + 1), len_ * sizeof(T));

  /*
  for (int j = 0; j < len_; j++) {
    slab_->items_[j] = slab_->items_[j+1];
  }
  */

  slab_->items_[len_] = 0;  // zero for GC scan
  return result;
}

template <typename T>
void List<T>::remove(T x) {
  int idx = this->index(x);
  this->pop(idx);  // unused
}

template <typename T>
void List<T>::clear() {
  if (slab_) {
    memset(slab_->items_, 0, len_ * sizeof(T));  // zero for GC scan
  }
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
  int n = other->len_;
  int new_len = len_ + n;
  reserve(new_len);

  for (int i = 0; i < n; ++i) {
    set(len_ + i, other->slab_->items_[i]);
  }
  len_ = new_len;
}

inline bool _cmp(Str* a, Str* b) {
  return mylib::str_cmp(a, b) < 0;
}

template <typename T>
void List<T>::sort() {
  std::sort(slab_->items_, slab_->items_ + len_, _cmp);
}

// TODO: mycpp can just generate the constructor instead?
// e.g. [None] * 3
template <typename T>
List<T>* list_repeat(T item, int times) {
  return NewList<T>(item, times);
}

// e.g. 'a' in ['a', 'b', 'c']
template <typename T>
inline bool list_contains(List<T>* haystack, T needle) {
  int n = len(haystack);
  for (int i = 0; i < n; ++i) {
    if (are_equal(haystack->index_(i), needle)) {
      return true;
    }
  }
  return false;
}

template <typename V>
List<Str*>* sorted(Dict<Str*, V>* d) {
  auto keys = d->keys();
  keys->sort();
  return keys;
}

template <typename T>
List<T>* sorted(List<T>* l) {
  auto ret = list(l);
  ret->sort();
  return ret;
}

// list(L) copies the list
template <typename T>
List<T>* list(List<T>* other) {
  auto result = NewList<T>();
  result->extend(other);
  return result;
}

#define GLOBAL_LIST(T, N, name, array)                                \
  GcGlobal<GlobalSlab<T, N>> _slab_##name = {                         \
      {kNotInPool, 0, kZeroMask, HeapTag::Global, kIsGlobal}, array}; \
  GcGlobal<GlobalList<T, N>> _list_##name = {                         \
      {kNotInPool, 0, kZeroMask, HeapTag::Global, kIsGlobal},         \
      {N, N, &_slab_##name.obj}};                                     \
  List<T>* name = reinterpret_cast<List<T>*>(&_list_##name.obj);

template <class T>
class ListIter {
 public:
  explicit ListIter(List<T>* L) : L_(L), i_(0) {
    // Cheney only: L_ could be moved during iteration.
    // gHeap.PushRoot(reinterpret_cast<RawObject**>(&L_));
  }

  ~ListIter() {
    // gHeap.PopRoot();
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
  T iterNext() {
    if (Done()) {
      throw Alloc<StopIteration>();
    }
    T ret = L_->slab_->items_[i_];
    Next();
    return ret;
  }

  // only for use with generators
  List<T>* GetList() {
    return L_;
  }

 private:
  List<T>* L_;
  int i_;
};

// list(it) returns the iterator's backing list
template <typename T>
List<T>* list(ListIter<T> it) {
  return list(it.GetList());
}

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

int max(List<int>* elems);

#endif  // MYCPP_GC_LIST_H
