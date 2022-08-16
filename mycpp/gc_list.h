#ifndef LIST_TYPES_H
#define LIST_TYPES_H

template <typename T>
class List : public Obj {
  // TODO: Move methods that don't allocate or resize: out of gc_heap?
  // - allocate: append(), extend()
  // - resize: pop(), clear()
  // - neither: reverse(), sort() -- these are more like functions.  Except
  //   sort() is a templated method that depends on type param T.
  // - neither: index(), slice()

 public:
  List() : Obj(Tag::FixedSize, maskof_List(), sizeof(List<T>)) {
    // Ensured by heap zeroing.  It's never directly on the stack.
    assert(len_ == 0);
    assert(capacity_ == 0);
    assert(slab_ == nullptr);
  }

  // Implements L[i]
  T index_(int i) {
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
  void set(int i, T item) {
    slab_->items_[i] = item;
  }

  // L[begin:]
  List* slice(int begin) {
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
  List* slice(int begin, int end) {
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
  T pop() {
    assert(len_ > 0);
    len_--;
    T result = slab_->items_[len_];
    slab_->items_[len_] = 0;  // zero for GC scan
    return result;
  }

  // Used in osh/word_parse.py to remove from front
  // TODO: Don't accept an arbitrary index?
  T pop(int i) {
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

  void clear() {
    memset(slab_->items_, 0, len_ * sizeof(T));  // zero for GC scan
    len_ = 0;
  }

  // Used in osh/string_ops.py
  void reverse() {
    for (int i = 0; i < len_ / 2; ++i) {
      // log("swapping %d and %d", i, n-i);
      T tmp = slab_->items_[i];
      int j = len_ - 1 - i;
      slab_->items_[i] = slab_->items_[j];
      slab_->items_[j] = tmp;
    }
  }

  // Templated function
  void sort();

  // 8 / 4 = 2 items, or 8 / 8 = 1 item
  static const int kCapacityAdjust = kSlabHeaderSize / sizeof(T);
  static_assert(kSlabHeaderSize % sizeof(T) == 0,
                "Slab header size should be multiple of item size");

  // Ensure that there's space for a number of items
  void reserve(int n) {
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

  // Append a single element to this list.  Must be specialized List<int> vs
  // List<Str*>.
  void append(T item);

  // Extend this list with multiple elements.
  void extend(List<T>* other) {
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

#endif // LIST_TYPES_H
