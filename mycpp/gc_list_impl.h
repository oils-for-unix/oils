#ifndef LIST_IMPL_H
#define LIST_IMPL_H

#if 0

 public:
  // Note: constexpr doesn't work because the std::vector destructor is
  // nontrivial
  List() : Obj(Tag::FixedSize, kZeroMask, 0), v_() {
    // Note: this seems to INCREASE the number of 'new' calls.  I guess because
    // many 'spids' lists aren't used?
    // v_.reserve(64);
  }

  // Used by list_repeat
  List(T item, int n) : Obj(Tag::FixedSize, kZeroMask, 0), v_(n, item) {
  }

  List(std::initializer_list<T> init)
      : Obj(Tag::FixedSize, kZeroMask, 0), v_() {
    for (T item : init) {
      v_.push_back(item);
    }
  }

  // a[-1] = 42 becomes a->set(-1, 42);
  void set(int index, T value) {
    if (index < 0) {
      index = v_.size() + index;
    }
    v_[index] = value;
  }

  // L[i]
  T index_(int i) const {
    if (i < 0) {
      // User code doesn't result in mylist[-1], but Oil's own code does
      int j = v_.size() + i;
      return v_.at(j);
    }
    return v_.at(i);  // checked version
  }

  // L.index(i) -- Python method
  int index(T value) const {
    int len = v_.size();
    for (int i = 0; i < len; i++) {
      // TODO: this doesn't work for strings!
      if (v_[i] == value) {
        return i;
      }
    }
    throw new ValueError();
  }

  // L[begin:]
  List* slice(int begin) {
    if (begin == 0) {
      return this;
    }
    if (begin < 0) {
      begin = v_.size() + begin;
    }

    List* result = new List();
    int len = v_.size();
    for (int i = begin; i < len; i++) {
      result->v_.push_back(v_[i]);
    }
    return result;
  }
  // L[begin:end]
  // TODO: Can this be optimized?
  List* slice(int begin, int end) {
    if (begin < 0) {
      begin = v_.size() + begin;
    }
    if (end < 0) {
      end = v_.size() + end;
    }

    List* result = new List();
    for (int i = begin; i < end; i++) {
      result->v_.push_back(v_[i]);
    }
    return result;
  }

  void append(T item) {
#ifdef ALLOC_LOG
    // we can post process this format to find large lists
    // except when they're constants, but that's OK?
    printf("%p %zu\n", this, v_.size());
#endif

    v_.push_back(item);
  }

  void extend(List<T>* items) {
    // Note: C++ idioms would be v_.insert() or std::copy, but we're keeping it
    // simple.
    //
    // We could optimize this for the small cases Oil has?  I doubt it's a
    // bottleneck anywhere.
    int len = items->v_.size();
    for (int i = 0; i < len; ++i) {
      v_.push_back(items->v_[i]);
    }
  }

  // Reconsider?
  // https://stackoverflow.com/questions/12600330/pop-back-return-value
  T pop() {
    assert(!v_.empty());
    T result = v_.back();
    v_.pop_back();
    return result;
  }

  // Used in osh/word_parse.py to remove from front
  // TODO: Don't accept arbitrary index?
  T pop(int index) {
    if (v_.size() == 0) {
      // TODO(Jesse): Probably shouldn't crash if we try to pop a List with
      // nothing on it
      InvalidCodePath();
    }

    T result = v_.at(index);
    v_.erase(v_.begin() + index);
    return result;

    /*
    Implementation without std::vector
    assert(index == 0);
    for (int i = 1; i < v_.size(); ++i) {
      v_[i-1] = v_[i];
    }
    v_.pop_back();
    */
  }

  void clear() {
    v_.clear();
  }

  void sort() {
    mysort(&v_);
  }

  // in osh/string_ops.py
  void reverse() {
    int n = v_.size();
    for (int i = 0; i < n / 2; ++i) {
      // log("swapping %d and %d", i, n-i);
      T tmp = v_[i];
      int j = n - 1 - i;
      v_[i] = v_[j];
      v_[j] = tmp;
    }
  }

  // private:
  std::vector<T> v_;  // ''.join accesses this directly
#endif


bool are_equal(Tuple2<Str*, int>* t1, Tuple2<Str*, int>* t2);
bool are_equal(int, int);

  // Implements L[i]
template <typename T>
T List<T>::index_(int i) {

#if 0
  if (i < 0) {
    i += len_; // NOTE(Jesse): the fuck?
  }

  if (i < len_) {
    return slab_->items_[i];
  }

  log("i = %d, len_ = %d", i, len_);
  InvalidCodePath();  // Out of bounds
#else

  // NOTE(Jesse): This is fucked, but less fucked than the 'gc' version
  if (i < 0) {
    int j = len_ + i;
    assert(j < len_);
    return slab_->items_[j];
  }

  assert(i < len_);
  return slab_->items_[i];
#endif
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
#if 0
  slab_->items_[i] = item;
#endif
  if (i < 0) {
    i = len_ + i;
  }
  slab_->items_[i] = item;
}

// L[begin:]
template <typename T>
List<T>* List<T>::slice(int begin) {// @todo_old_impl
#if 0
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
#endif

  if (begin < 0) {
    begin = len_ + begin;
  }

  // TODO(Jesse): Pretty much guaranteed these will fire
  /* assert(begin < len_); */
  /* assert(end < len_); */

  /* assert(begin > -1); */
  /* assert(end > -1); */

  auto old_this = this;

  List<T> *result = NewList<T>();
  assert(old_this == this);

  for (int i = begin; i < len_; i++) {
    result->append(this->slab_->items_[i]);
  }

  return result;
}

  // L[begin:end]
  // TODO: Can this be optimized?
template <typename T>
List<T>* List<T>::slice(int begin, int end) {
#if 0
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
#endif

  if (begin < 0) {
    begin = len_ + begin;
  }
  if (end < 0) {
    end = len_ + end;
  }
  //
  // TODO(Jesse): Pretty much guaranteed these will fire
  /* assert(begin < len_); */
  /* assert(end < len_); */

  /* assert(begin > -1); */
  /* assert(end > -1); */


  List<T> *result = NewList<T>();
  for (int i = begin; i < end; i++) {
    result->append(slab_->items_[i]);
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
void List<T>::reverse() {// @todo_old_impl
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
void List<T>::reserve(int n) {// @todo_old_impl
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
void List<T>::extend(List<T>* other) {// @todo_old_impl
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
List<Str*>* sorted(Dict<Str*, V>* d) {// @todo_old_impl
  auto keys = d->keys();
  keys->sort();
  return keys;
}


#endif // LIST_IMPL_H
