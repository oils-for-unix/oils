#ifndef LIST_IMPL_H
#define LIST_IMPL_H

  // Implements L[i]
template <typename T>
T List<T>::index_(int i) {
  if (i < 0) {
    i += len_;
  }

  if (i < len_) {
    return slab_->items_[i];
  }

  log("i = %d, len_ = %d", i, len_);
  InvalidCodePath();  // Out of bounds
}

// Implements L[i] = item
// Note: Unlike Dict::set(), we don't need to specialize List::set() on T for
// StackRoots because it doesn't allocate.
template <typename T>
void List<T>::set(int i, T item) {
  slab_->items_[i] = item;
}

// L[begin:]
template <typename T>
List<T>* List<T>::slice(int begin) {
  auto self = this;
  List<T>* result = nullptr;
  StackRoots _roots({&self, &result});

  if (begin == 0) {
    return self;
  }
  if (begin < 0) {
    begin = self->len_ + begin;
  }

  result = Alloc<List<T>>();  // TODO: initialize with size
  for (int i = begin; i < self->len_; i++) {
    result->append(self->slab_->items_[i]);
  }
  return result;
}

  // L[begin:end]
  // TODO: Can this be optimized?
template <typename T>
List<T>* List<T>::slice(int begin, int end) {
  auto self = this;
  List<T>* result = nullptr;
  StackRoots _roots({&self, &result});

  if (begin < 0) {
    begin = self->len_ + begin;
  }
  if (end < 0) {
    end = self->len_ + end;
  }

  result = Alloc<List<T>>();  // TODO: initialize with size
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
template <typename T>
T List<T>::pop(int i) {
  assert(len_ > 0);
  assert(i == 0);  // only support popping the first item

  len_--;
  T result = index_(0);

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

#if 0
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

#endif // 0

template<typename T>
void List<T>::sort() {
  NotImplemented();
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
#endif // LIST_IMPL_H
