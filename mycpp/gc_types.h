// mycpp/gc_types.h
//
// Definitions of Str, List<T>, Dict<K, V>, and related functions.

#ifndef GC_TYPES_H
#define GC_TYPES_H

#include "mycpp/gc_heap.h"

namespace gc_heap {

template <typename T>
inline void InitSlabCell(Obj* obj) {
  // log("SCANNED");
  obj->heap_tag_ = Tag::Scanned;
}

template <>
inline void InitSlabCell<int>(Obj* obj) {
  // log("OPAQUE");
  obj->heap_tag_ = Tag::Opaque;
}

// don't include items_[1]
const int kSlabHeaderSize = sizeof(Obj);

// Opaque slab, e.g. for List<int>
template <typename T>
class Slab : public Obj {
 public:
  Slab(int obj_len) : Obj(0, 0, obj_len) {
    InitSlabCell<T>(this);
  }
  T items_[1];  // variable length
};

template <typename T, int N>
class GlobalSlab {
  // A template type with the same layout as Str with length N-1 (which needs a
  // buffer of size N).  For initializing global constant instances.
 public:
  OBJ_HEADER()

  T items_[N];

  DISALLOW_COPY_AND_ASSIGN(GlobalSlab)
};

// Note: entries will be zero'd because the Heap is zero'd.
template <typename T>
inline Slab<T>* NewSlab(int len) {
  int obj_len = RoundUp(kSlabHeaderSize + len * sizeof(T));
  void* place = gHeap.Allocate(obj_len);
  auto slab = new (place) Slab<T>(obj_len);  // placement new
  return slab;
}

#ifdef MYLIB_LEAKY
  #define GLOBAL_STR(name, val) Str* name = new Str(val);
  #define GLOBAL_LIST(T, N, name, array) List<T>* name = new List<T>(array);
#endif

#ifndef MYLIB_LEAKY

//
// Str
//

class Str : public gc_heap::Obj {
 public:
  // Don't call this directly.  Call AllocStr() instead, which calls this.
  explicit Str() : Obj(Tag::Opaque, kZeroMask, 0) {
    // log("GC Str()");
  }

  char* data() {
    return data_;
  };

  void SetObjLenFromStrLen(int str_len);

  Str* index_(int i);
  Str* slice(int begin);
  Str* slice(int begin, int end);

  Str* strip();
  // Used for CommandSub in osh/cmd_exec.py
  Str* rstrip(Str* chars);
  Str* rstrip();

  Str* ljust(int width, Str* fillchar);
  Str* rjust(int width, Str* fillchar);

  bool startswith(Str* s);
  bool endswith(Str* s);

  Str* replace(Str* old, Str* new_str);
  Str* join(List<Str*>* items);
  List<Str*>* split(Str* sep);

  bool isdigit();
  bool isalpha();
  bool isupper();

  Str* upper() {
    NotImplemented();  // Uncalled
  }

  Str* lower() {
    NotImplemented();  // Uncalled
  }

  // Other options for fast comparison / hashing / string interning:
  // - unique_id_: an index into intern table.  I don't think this works unless
  //   you want to deal with rehashing all strings when the set grows.
  //   - although note that the JVM has -XX:StringTableSize=FIXED, which means
  //   - it can degrade into linked list performance
  // - Hashed strings become GLOBAL_STR().  Never deallocated.
  // - Hashed strings become part of the "large object space", which might be
  //   managed by mark and sweep.  This requires linked list overhead.
  //   (doubly-linked?)
  // - Intern strings at GARBAGE COLLECTION TIME, with
  //   LayoutForwarded::new_location_?  Is this possible?  Does it introduce
  //   too much coupling between strings, hash tables, and GC?
  int hash_value_;
  char data_[1];  // flexible array

 private:
  int _strip_left_pos();
  int _strip_right_pos();

  DISALLOW_COPY_AND_ASSIGN(Str)
};

constexpr int kStrHeaderSize = offsetof(Str, data_);

inline void Str::SetObjLenFromStrLen(int str_len) {
  obj_len_ = kStrHeaderSize + str_len + 1;  // NUL terminator
}

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

extern Str* kEmptyString;

  // This macro is a workaround for the fact that it's impossible to have a
  // a constexpr initializer for char[N].  The "String Literals as Non-Type
  // Template Parameters" feature of C++ 20 would have done it, but it's not
  // there.
  //
  // https://old.reddit.com/r/cpp_questions/comments/j0khh6/how_to_constexpr_initialize_class_member_thats/
  // https://stackoverflow.com/questions/10422487/how-can-i-initialize-char-arrays-in-a-constructor

  #define GLOBAL_STR(name, val)                 \
    gc_heap::GlobalStr<sizeof(val)> _##name = { \
        Tag::Global,                            \
        0,                                      \
        gc_heap::kZeroMask,                     \
        gc_heap::kStrHeaderSize + sizeof(val),  \
        -1,                                     \
        val};                                   \
    Str* name = reinterpret_cast<Str*>(&_##name);

// Notes:
// - sizeof("foo") == 4, for the NUL terminator.
// - gc_heap_test.cc has a static_assert that GlobalStr matches Str.  We don't
// put it here because it triggers -Winvalid-offsetof

//
// String "Constructors".  We need these because of the "flexible array"
// pattern.  I don't think "new Str()" can do that, and placement new would
// require mycpp to generate 2 statements everywhere.
//

// New string of a certain length, to be filled in
inline Str* AllocStr(int len) {
  int obj_len = kStrHeaderSize + len + 1;  // NUL terminator
  void* place = gHeap.Allocate(obj_len);
  auto s = new (place) Str();
  s->SetObjLen(obj_len);  // So the GC can copy it
  return s;
}

// Like AllocStr, but allocate more than you need, e.g. for snprintf() to write
// into.  CALLER IS RESPONSIBLE for calling s->SetObjLenFromStrLen() afterward!
inline Str* OverAllocatedStr(int len) {
  int obj_len = kStrHeaderSize + len + 1;  // NUL terminator
  void* place = gHeap.Allocate(obj_len);
  auto s = new (place) Str();
  return s;
}

inline Str* StrFromC(const char* data, int len) {
  // Problem: if data points inside a Str, it's often invalidated!
  Str* s = AllocStr(len);

  // log("AllocStr s->data_ %p len = %d", s->data_, len);
  // log("sizeof(Str) = %d", sizeof(Str));
  memcpy(s->data_, data, len);
  assert(s->data_[len] == '\0');  // should be true because Heap was zeroed

  return s;
}

// CHOPPED OFF at internal NUL.  Use explicit length if you have a NUL.
inline Str* StrFromC(const char* data) {
  return StrFromC(data, strlen(data));
}

bool str_equals(Str* left, Str* right);
bool maybe_str_equals(Str* left, Str* right);

//
// Compile-time computation of GC field masks.
//

class _DummyObj {  // For maskbit()
 public:
  OBJ_HEADER()
  int first_field_;
};

constexpr int maskbit(int offset) {
  return 1 << ((offset - offsetof(_DummyObj, first_field_)) / sizeof(void*));
}

class _DummyObj_v {  // For maskbit_v()
 public:
  void* vtable;  // how the compiler does dynamic dispatch
  OBJ_HEADER()
  int first_field_;
};

constexpr int maskbit_v(int offset) {
  return 1 << ((offset - offsetof(_DummyObj_v, first_field_)) / sizeof(void*));
}

//
// List<T>
//

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

  #define GLOBAL_LIST(T, N, name, array)                                \
    gc_heap::GlobalSlab<T, N> _slab_##name = {                          \
        Tag::Global, 0, gc_heap::kZeroMask, gc_heap::kNoObjLen, array}; \
    gc_heap::GlobalList<T, N> _list_##name = {                          \
        Tag::Global, 0, gc_heap::kZeroMask, gc_heap::kNoObjLen,         \
        N,           N, &_slab_##name};                                 \
    List<T>* name = reinterpret_cast<List<T>*>(&_list_##name);

// A list has one Slab pointer which we need to follow.
constexpr uint16_t maskof_List() {
  return maskbit(offsetof(GlobalList<int COMMA 1>, slab_));
}

template <typename T>
class List : public gc_heap::Obj {
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

inline bool keys_equal(int left, int right) {
  return left == right;
}

inline bool keys_equal(Str* left, Str* right) {
  return str_equals(left, right);
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
class Dict : public gc_heap::Obj {
 public:
  Dict() : gc_heap::Obj(Tag::FixedSize, maskof_Dict(), sizeof(Dict)) {
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

#endif  // MYLIB_LEAKY

}  // namespace gc_heap

#ifndef MYLIB_LEAKY

// Do some extra calculation to avoid storing redundant lengths.
inline int len(const gc_heap::Str* s) {
  return s->obj_len_ - gc_heap::kStrHeaderSize - 1;
}

template <typename T>
int len(const gc_heap::List<T>* L) {
  return L->len_;
}

template <typename K, typename V>
inline int len(const gc_heap::Dict<K, V>* d) {
  return d->len_;
}

#endif  // MYLIB_LEAKY

#endif  // GC_TYPES_H
