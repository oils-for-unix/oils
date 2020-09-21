// Simplest garbage collector that will work.
//
// It's a semi-space collector.  (Later we could add a "large object space",
// managed by mark-and-sweep after each copy step.)
//
// Design:
// - Immutable Slab and Str (difference: Str has a hash for quick lookup?)
// - Mutable List, Dict that point to Slab
//   - List::append() and extend() can realloc
//   - Dict::set() can realloc and rehash
//
// TODO:
// - Prototype Handle<T> and HandleScope for stack roots
// - Copying GC algorithm over Cell*!
//   - Write a simple benchmark that triggers GC over and over.  Maybe put it
//     in a single function, and populate stack roots manually.
// - Dicts should actually use hashing!  Test computational complexity.
//
// - Figure out what happens with GLOBAL Str* instances
//   - should not be copied!  Do they have a special tag in the Cell header?
//   - can they be constexpr in the generated source?  Would be nice I think.

// Memory allocation APIs:
//
// - gc_alloc<Foo>(x)
//   An alternative to new Foo(x).  mycpp/ASDL should generate these calls.
//   Automatically deallocated.
// - mylib::Alloc()
//   For Slab, and for special types like Str.  Automatically deallocated.
// - malloc() -- for say yajl to use.  Manually deallocated.
// - new/delete -- for other C++ libs to use.  Manually deallocated.
//
// Slab Sizing with 8-byte slab header
//
//   16 - 8 =  8 = 1 eight-byte or  2 four-byte elements
//   32 - 8 = 24 = 3 eight-byte or  6 four-byte elements
//   64 - 8 = 56 = 7 eight-byte or 14 four-byte elements
//
// But dict will have DIFFERENT size keys and values!  Like Dict<int, Str*>
//
// Capacity check without division:
//
//   kSlabHeaderSize + n * sizeof(T) >= slab->cell_len_
//   where n is the number of elements we want to store
//   if it's equal then it's OK I guess
//   For dict, use indices
//
// Small Size Optimization: omit separate slabs (later)
//
// - List: 24 bytes, so we could get 1 or 2 entries for free?  That might add
//   up
// - Dict: 40 bytes: I don't think it optimizes
// - Doesn't apply to Str because it's immutable: 16 bytes + string length.

#include <cassert>  // assert()
#include <cstdarg>  // va_list, etc.
#include <cstddef>  // max_align_t
#include <cstdint>  // max_align_t
#include <cstdio>   // vprintf
#include <cstdlib>  // malloc
#include <cstring>  // memcpy
#include <initializer_list>
#include <new>      // placement new
#include <utility>  // std::forward

#include "greatest.h"

void log(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vprintf(fmt, args);
  va_end(args);
  puts("");
}

class Cell;

class Heap {
 public:
  Heap() {  // default constructor does nothing -- relies on zero initialization
  }

  // real initialization
  void Init(int num_bytes) {
    from_space_ = static_cast<char*>(malloc(num_bytes));
    to_space_ = static_cast<char*>(malloc(num_bytes));

    // slab scanning relies on 0 bytes (nullptr)
    memset(from_space_, 0, num_bytes);
    memset(to_space_, 0, num_bytes);

    space_size_ = num_bytes;
    alloc_pos_ = 0;

    roots_top_ = 0;
  }

  void AddRoot(void* p) {
    roots_[roots_top_++] = p;
  }

  Cell* Relocate(Cell* cell);
  void Collect();

  char* from_space_;
  char* to_space_;
  char* cur_space_;  // femtolisp has this?  Do we need it?
  // femtolisp also has lim_?

  char* scan_;  // boundary between black and grey
  char* free_;  // next place to

  int space_size_;  // current size
  int alloc_pos_;   // where to allocate next

  bool grew_;  // did we grow the last time?

  // Stack roots.  The obvious data structure is a linked list, but an array
  // has better locality.
  //
  // femtolisp uses a global pointer to dynamically-allocated growable array,
  // with initial N_STACK = 262144!  Kind of arbitrary.

  int roots_top_;
  // TODO: This should be Handle, because we need to call .update(new_loc) on
  // it?
  void* roots_[1024];  // max

  // Note: should we have a stack of handle scopes here?  So we don't have to
  // declare HandleScope h(5) correctly.
  //
  // problem: what about f(NewStr("x")) or f(gc_alloc<List<int>>({42})) ?
  // Then those pointers never gets wrapped in a handle.
  //
  // Example:
  // f->WriteRaw((new Tuple2<Str*, int>(s, num_chars)));
  //
  // it could technically collect itself!
  //
  // this->mem->SetVar(new lvalue::Named(fd_name), new value::Str(str(fd)),
  // scope_e::Dynamic);
  //
  // Do there have to be Handle<T> for all function arguments then?  They are
  // immediately copied into andles I guess.

  // TODO:
  //   scan pointer, next pointer
  //   reallocation policy?
};

// TODO: Make this a thread local?
Heap gHeap;

// handles get registered here, and they appear on the heap somehow
class HandleScope {
 public:
  HandleScope(int num_locals) : num_locals_(num_locals) {
  }
  ~HandleScope() {
    // prepare for the next function call
    gHeap.roots_top_ -= num_locals_;
  }
  int num_locals_;
};

// TODO: how to implement this?
// behaves like a pointer
template <typename T>
class Handle {
 public:
  explicit Handle(T* raw_pointer) : raw_pointer_(raw_pointer) {
    gHeap.AddRoot(this);
  }

    // This would allow us to transparently pass Handle<Str> to a function
    // expecting Str*, but it's dangerous:
    //
    // https://www.informit.com/articles/article.aspx?p=31529&seqNum=7
    //
    // Although maybe it's not dangerous if we audit every single function in
    // mylib?  Policy:
    //
    // - It either accept a Handle<>
    // - Or it accepts a raw pointer and DOES NOT ALLOCATE anywhere
    //
    // The benefit to this is that you don't have to have TWO FUNCTIONS:
    //
    // len(node->left)  # raw pointer
    // len(local_var)  # Handle
    //
    // However I think putting .get() at the call site in mycpp is more
    // explicit. The readability of the generated code is important!

#if 0
  operator T*() {
    return raw_pointer_;
  }
#endif

  // dereference to get the real value
  // note: we could call this deref() or value() to avoid operator overloading.
  T operator*() const {
    log("operator*");
    return *raw_pointer_;
  }
  T* operator->() const {
    log("operator->");
    return raw_pointer_;
  }

  T* get() const {
    return raw_pointer_;
  }

  // called by the garbage collector when moved to a new location!
  void update(T* moved) {
    raw_pointer_ = moved;
  }

  T* raw_pointer_;
};

// 1 MiB, and will double when necessary.  Note: femtolisp uses 512 KiB.
const int kInitialSize = 1 << 20;

constexpr int kMask = alignof(max_align_t) - 1;  // e.g. 15 or 7

// Align returned pointers to the worst case of 8 bytes (64-bit pointers)
inline size_t aligned(size_t n) {
  // https://stackoverflow.com/questions/2022179/c-quick-calculation-of-next-multiple-of-4
  // return (n + 7) & ~7;

  return (n + kMask) & ~kMask;
}

void* Alloc(int size) {
  char* p = gHeap.from_space_ + gHeap.alloc_pos_;
  gHeap.alloc_pos_ += aligned(size);
  return p;
}

// Variadic templates:
// https://eli.thegreenplace.net/2014/variadic-templates-in-c/
template <typename T, typename... Args>
T* gc_alloc(Args&&... args) {
  void* place = Alloc(sizeof(T));

  if (place == nullptr) {  // not enough space
    // TODO: what happens after collection if there's still not enough space?
    // I think we should grow it first.
    //
    // So Alloc() shouldn't return nullptr.  It should return if we're 90%
    // full?
    //
    // femtolisp has gc(int mustgrow)
    //
    // And actually it does it in while loop!  You could have an allocation so
    // big that you need to grow twice???  Passing the amount seems better?

    gHeap.Collect();
  }

  // placement new
  return new (place) T(std::forward<Args>(args)...);
}

// Return the size of a resizeable allocation.  For now we just round up by
// powers of 2. This could be optimized later.  CPython has an interesting
// policy in listobject.c.
//
// https://stackoverflow.com/questions/466204/rounding-up-to-next-power-of-2
int RoundUp(int n) {
  // minimum size
  if (n < 8) {
    return 8;
  }

  // TODO: what if int isn't 32 bits?
  n--;
  n |= n >> 1;
  n |= n >> 2;
  n |= n >> 4;
  n |= n >> 8;
  n |= n >> 16;
  n++;
  return n;
}

const int kZeroMask = 0;

namespace Tag {
const int Forwarded = 1;
const int Opaque = 2;     // Copy but don't scan.  List<int> and Str
const int FixedSize = 3;  // Fixed size headers: consult field_mask_
const int Scanned = 4;    // Copy AND scan for non-NULL pointers.
}  // namespace Tag

class Cell {
  // The unit of garbage collection.  It has a header describing how to find
  // the pointers within it.
  //
  // Note: Sorting ASDL fields by (non-pointer, pointer) is a good idea, but it
  // breaks down because mycpp has inheritance.  Could do this later.

 public:
  Cell() : tag(0), field_mask_(0), cell_len_(0) {
  }
  Cell(uint16_t tag) : tag(tag), field_mask_(0), cell_len_(0) {
  }
  Cell(uint16_t tag, uint16_t field_mask, int cell_len)
      : tag(tag), field_mask_(field_mask), cell_len_(cell_len) {
  }

  void SetCellLength(int cell_len) {
    this->cell_len_ = cell_len;
  }

  uint16_t tag;  // ASDL tags are 0 to 255
                 // Tag::Forwarded is 256?
                 // We could also reserve tags for Str, List, and Dict
                 // Then do we have 7 more bits for the GC strategy / length?
  uint16_t field_mask_;  // for fixed length records, so max 16 fields

  // # bytes to copy, or # bytes to scan?
  // for Slab, which is used by List<Str*> and Dict<Str*, Str*>
  //
  // Should this be specific to slab?  If tag == Tag::*Slab?
  // TODO: if we limit it to 15 fields, we can encode length in field_mask.
  uint32_t cell_len_;
};

class Forwarded : public Cell {
 public:
  // only valid if tag == Tag::Forwarded
  Cell* new_location;
};

// for Tag::FixedSize
class FixedCell : public Cell {
 public:
  Cell* children_[16];  // only entries with field_mask will be valid
};

template <typename T>
void InitSlabCell(Cell* cell) {
  // log("SCANNED");
  cell->tag = Tag::Scanned;
}

template <>
void InitSlabCell<int>(Cell* cell) {
  // log("OPAQUE");
  cell->tag = Tag::Opaque;
}

// don't include items_[1]
const int kSlabHeaderSize = sizeof(Cell);

// Opaque slab.  e.g. for String data
template <typename T>
class Slab : public Cell {
 public:
  Slab(int cell_len) : Cell(0, 0, cell_len) {
    InitSlabCell<T>(this);
  }
  T items_[1];  // minimum string cell_len_
};

// Note: entries should be zero'd because Alloc() just bumps the heap
template <typename T>
Slab<T>* NewSlab(int len) {
  int cell_len = RoundUp(kSlabHeaderSize + len * sizeof(T));
  void* place = Alloc(cell_len);
  auto slab = new (place) Slab<T>(cell_len);  // placement new
  return slab;
}

// Move an object from one space to another.
Cell* Heap::Relocate(Cell* cell) {
  // note: femtolisp has ismanaged() in addition to isforwarded()
  // ismanaged() could be for globals

  // it handles TAG_CONS, TAG_VECTOR, TAG_CPRIM, TAG_CVALUE, (we might want
  // this), TAG_FUNCTION, TAG_SYM
  //
  // We have fewer cases than that.  We just use a Cell.

  if (cell->tag == Tag::Forwarded) {
    auto f = reinterpret_cast<Forwarded*>(cell);
    return f->new_location;
  } else {
    auto new_location = reinterpret_cast<Cell*>(free_);
    int n = cell->cell_len_;
    memcpy(new_location, cell, n);
    free_ += n;
    auto f = reinterpret_cast<Forwarded*>(cell);
    f->tag = Tag::Forwarded;
    f->new_location = new_location;
    return new_location;
  }
}

void Heap::Collect() {
  log("--- COLLECT");

  // Copy policy from femtolisp for now:
  //
  // If we're using > 80% of the space, resize tospace so we have more space to
  // fill next time. if we grew tospace last time, grow the other half of the
  // heap this time to catch up.

  // char* tmp = from_space_;
  // from_space_ = to_space_;
  // to_space_ = tmp;

  scan_ = to_space_;  // boundary between black and gray
  free_ = to_space_;  // where to copy new entries

  for (int i = 0; i < roots_top_; ++i) {
    auto handle = static_cast<Handle<void>*>(roots_[i]);
    auto root = reinterpret_cast<Cell*>(handle->get());

    log("%d. handle %p", i, handle);
    log("     root %p", root);

    // This updates the underlying Str/List/Dict with a forwarding pointer,
    // i.e. for other objects that are pointing to it
    Cell* new_location = Relocate(root);

    // This update is for the "double indirection", so future accesses to a
    // local variable use the new location
    handle->update(new_location);
  }

  while (scan_ < free_) {
    auto cell = reinterpret_cast<Cell*>(scan_);
    switch (cell->tag) {
    case Tag::FixedSize: {
      auto fixed = reinterpret_cast<FixedCell*>(cell);
      int mask = fixed->field_mask_;
      for (int i = 0; i < 16; ++i) {
        if (mask & (1 << i)) {
          Cell* child = fixed->children_[i];
          // log("i = %d, p = %p, tag = %d", i, child, child->tag);
          fixed->children_[i] = Relocate(child);
        }
      }
      break;
    }
    case Tag::Scanned: {
      auto slab = reinterpret_cast<Slab<void*>*>(cell);
      int n = (slab->cell_len_ - kSlabHeaderSize) / sizeof(void*);
      for (int i = 0; i < n; ++i) {
        Cell* child = reinterpret_cast<Cell*>(slab->items_[i]);
        if (child == nullptr) {
          break;
        }
        slab->items_[i] = Relocate(child);
      }
      break;
    }
      // other tags like Tag::Opaque have no children
      // TODO: I think we also want Tag::SparseScannedSlab for Dict
    }
    scan_ += cell->cell_len_;
  }
}

class Str : public Cell {
 public:
  // Note: shouldn't be called directly.  Call NewStr().
  Str(int len) : Cell(Tag::Opaque), len_(len) {
  }
  // Note: OCaml unifies the cell length and string length with padding 00, 00
  // 01, 00 00 02, 00 00 00 03.  Although I think they added special cases for
  // 32-bit and 64-bit; we're using the portable max_align_t
  int len_;
  int unique_id_;   // index into intern table ?
  char opaque_[1];  // flexible array
};

const int kStrHeaderSize = sizeof(Cell) + sizeof(int) + sizeof(int);

// This is one slab in the second position.  TODO: This is different for 32
// bit???  Is there a way to make it portable?
const int kListMask = 0x0002;  // in binary: 0b 0000 0000 0000 00010

template <typename T>
class List : public Cell {
 public:
  List()
      : Cell(Tag::FixedSize, kListMask, sizeof(List<T>)),
        len_(0),
        capacity_(0),
        slab_(nullptr) {
  }

  // TODO: are we using this?
  List(std::initializer_list<T> init)
      : Cell(Tag::FixedSize, kListMask, sizeof(List<T>)), slab_(nullptr) {
    extend(init);
  }

  // Implements L[i]
  T index(int i) {
    if (i < len_) {
      return slab_->items_[i];
    } else {
      assert(0);  // Out of bounds
    }
  }

  // Implements L[i] = item
  void set(int i, T item) {
    slab_->items_[i] = item;
  }

  // 8 / 4 = 2 items, or 8 / 8 = 1 item
  static const int kCapacityAdjust = kSlabHeaderSize / sizeof(T);
  static_assert(kSlabHeaderSize % sizeof(T) == 0,
                "Slab header size should be multiple of item size");

  // Ensure that there's space for a number of items
  void reserve(int n) {
    if (slab_) {
      log("reserve capacity = %d, n = %d", capacity_, n);
    }

    if (capacity_ < n) {
      // Example: The user asks for space for 7 integers.  Account for the
      // header, and say we need 9 to determine the cell length.  9 is rounded
      // up to 16, for a 64-byte cell.  Then we actually have space for 14
      // items.
      capacity_ = RoundUp(n + kCapacityAdjust) - kCapacityAdjust;
      auto new_slab = NewSlab<T>(capacity_);

      // slab_ may not be initialized constructor because many lists are empty.
      if (capacity_ != 0) {
        // log("Copying %d bytes", len_ * sizeof(T));
        memcpy(new_slab->items_, slab_->items_, len_ * sizeof(T));
      }
      slab_ = new_slab;
    }
    // Otherwise, there's enough capacity
  }

  // Append a single element to this list
  void append(T item) {
    reserve(len_ + 1);
    set(len_, item);
    ++len_;
  }

  // Extend this list with multiple elements.  TODO: overload to take a List<> ?
  void extend(std::initializer_list<T> init) {
    int n = init.size();

    reserve(len_ + n);

    int i = len_;
    for (auto item : init) {
      set(i, item);
      ++i;
    }

    len_ += n;
  }

  int len_;       // number of entries
  int capacity_;  // max entries before resizing

  // The container may be resized, so this field isn't in-line.
  Slab<T>* slab_;
};

template <typename K>
int find_by_key(Slab<K>* keys_, int len, int key) {
  for (int i = 0; i < len; ++i) {
    if (keys_->items_[i] == key) {
      return i;
    }
  }
  return -1;
}

inline bool str_equals(Str* left, Str* right) {
  if (left->len_ == right->len_) {
    return memcmp(left->opaque_, right->opaque_, left->len_) == 0;
  } else {
    return false;
  }
}

// TODO: need sentinel for deletion.  The sentinel is in the *indices* array,
// not in keys or values.  Those are copied verbatim, but may be sparse because
// of deletions?

template <typename K>
int find_by_key(Slab<K>* keys_, int len, Str* key) {
  for (int i = 0; i < len; ++i) {
    if (str_equals(keys_->items_[i], key)) {
      return i;
    }
  }
  return -1;
}

// This is three slab pointers after 2 integers.  TODO: portability?
const int kDictMask = 0x000E;  // in binary: 0b 0000 0000 0000 01110

template <class K, class V>
class Dict : public Cell {
 public:
  Dict()
      : Cell(Tag::FixedSize, kDictMask, 0),
        len_(0),
        capacity_(0),
        index_(nullptr),
        keys_(nullptr),
        values_(nullptr) {
  }

  // This relies on the fact that containers of 4-byte ints are reduced by 2
  // items, which is greater than (or equal to) the reduction of any other type
  static const int kCapacityAdjust = kSlabHeaderSize / sizeof(int);
  static_assert(kSlabHeaderSize % sizeof(int) == 0,
                "Slab header size should be multiple of key size");

  void reserve(int n) {
    // log("--- reserve %d", capacity_);
    if (capacity_ < n) {
      // calculate the number of keys and values we should have
      capacity_ = RoundUp(n + kCapacityAdjust) - kCapacityAdjust;

      // TODO: This is SPARSE.  How to compute a size that ensures a decent
      // load factor?
      int index_len = capacity_;
      auto new_i = NewSlab<int>(index_len);

      // These are DENSE.
      auto new_k = NewSlab<K>(capacity_);
      auto new_v = NewSlab<V>(capacity_);

      if (keys_ != nullptr) {
        // Copy the old index.  Note: remaining entries should be zero'd
        // because of Alloc() behavior.
        memcpy(new_i->items_, index_->items_, index_->cell_len_);

        memcpy(new_k->items_, keys_->items_, len_ * sizeof(K));
        memcpy(new_v->items_, values_->items_, len_ * sizeof(V));
      }

      index_ = new_i;
      keys_ = new_k;
      values_ = new_v;
    }
  }

  // d[key] in Python: raises KeyError if not found
  V index(K key) {
    int pos = find(key);
    if (pos == -1) {
      assert(0);
    } else {
      return values_->items_[pos];
    }
  }

  // Implements d[k] = v.  May resize the dictionary.
  void set(K key, V val) {
    int pos = find(key);
    if (pos == -1) {
      reserve(len_ + 1);
      keys_->items_[len_] = key;
      values_->items_[len_] = val;
      ++len_;
    } else {
      values_->items_[pos] = val;
    }
  }

  // int index_size_;  // size of index (sparse)
  int len_;       // number of entries (keys and values, almost dense)
  int capacity_;  // number of entries before resizing

  // These 3 slabs are resized at the same time.
  Slab<int>* index_;  // dense indices which are themselves indexed by
                      //  hash value % capacity_
  Slab<K>* keys_;     // Dict<int, V>
  Slab<V>* values_;   // Dict<K, int>

 private:
  // returns the position in the array
  int find(K key) {
    return find_by_key(keys_, len_, key);
  }
};

//
// "Constructors"
//

// Note: This is NewStr() because of the "flexible array" pattern.
// I don't think "new Str()" can do that, and placement new would require mycpp
// to generate 2 statements everywhere.

Str* NewStr(const char* data, int len) {
  int cell_len = kStrHeaderSize + len;
  void* place = Alloc(cell_len);  // immutable, so allocate exactly this amount
  auto s = new (place) Str(len);
  memcpy(s->opaque_, data, len);
  s->SetCellLength(cell_len);  // is this right?

  return s;
}

Str* NewStr(const char* data) {
  return NewStr(data, strlen(data));
}

//
// Functions
//

// Note: we need this duplicate for now... Otherwise the implicit construction
// for len(Handle<Str>) leads to more stack roots than we think!  TODO: I think
// we need a better way of balancing it.  We don't want HandleScope h(5).
#if 1
int len(const Str* s) {
  return s->len_;
}
#endif

  // Hm only functions that don't allocate can take a raw pointer ...
  // If they allocate, then that pointer can be moved out from under them!

#if 1
// Hm do all standard library functions have to take Handles now?
int len(Handle<Str> s) {
  return s.get()->len_;
}
#endif

template <typename T>
int len(const List<T>* L) {
  return L->len_;
}

template <typename K, typename V>
inline int len(const Dict<K, V>* d) {
  return d->len_;
}

//
// Test Cases
//

// TODO:
// - Test what happens when a new string goes over the max heap size
//   - We want to resize the to_space, trigger a GC, and then allocate?  Or is
//     there something simpler?

TEST str_test() {
  auto str1 = NewStr("");
  auto str2 = NewStr("one\0two", 7);

  // Make sure they're on the heap
  int diff1 = reinterpret_cast<char*>(str1) - gHeap.from_space_;
  int diff2 = reinterpret_cast<char*>(str2) - gHeap.from_space_;
  ASSERT(diff1 < 1024);
  ASSERT(diff2 < 1024);

  ASSERT_EQ(0, len(str1));
  ASSERT_EQ(7, len(str2));

  ASSERT_EQ_FMT(Tag::Opaque, str1->tag, "%d");

  PASS();
}

// TODO:
//
// - Test what happens append() runs over the max heap size
//   - how does it trigger a collection?

TEST list_test() {
  auto list1 = gc_alloc<List<int>>();
  auto list2 = gc_alloc<List<Str*>>();

  ASSERT_EQ(0, len(list1));
  ASSERT_EQ(0, len(list2));

  ASSERT_EQ_FMT(0, list1->capacity_, "%d");
  ASSERT_EQ_FMT(0, list2->capacity_, "%d");

  ASSERT_EQ_FMT(Tag::FixedSize, list1->tag, "%d");
  ASSERT_EQ_FMT(Tag::FixedSize, list2->tag, "%d");

  // 8 byte cell header + 2 integers + pointer
  ASSERT_EQ_FMT(24, list1->cell_len_, "%d");
  ASSERT_EQ_FMT(24, list2->cell_len_, "%d");

  // Make sure they're on the heap
  int diff1 = reinterpret_cast<char*>(list1) - gHeap.from_space_;
  int diff2 = reinterpret_cast<char*>(list2) - gHeap.from_space_;
  ASSERT(diff1 < 1024);
  ASSERT(diff2 < 1024);

  list1->extend({11, 22, 33});
  ASSERT_EQ_FMT(3, len(list1), "%d");

  // 32 byte block - 8 byte header = 24 bytes, 6 elements
  ASSERT_EQ_FMT(6, list1->capacity_, "%d");
  ASSERT_EQ_FMT(Tag::Opaque, list1->slab_->tag, "%d");

  // 8 byte header + 3*4 == 8 + 12 == 20, rounded up to power of 2
  ASSERT_EQ_FMT(32, list1->slab_->cell_len_, "%d");

  ASSERT_EQ_FMT(11, list1->index(0), "%d");
  ASSERT_EQ_FMT(22, list1->index(1), "%d");
  ASSERT_EQ_FMT(33, list1->index(2), "%d");

  log("extending");
  list1->extend({44, 55, 66, 77});

  // 64 byte block - 8 byte header = 56 bytes, 14 elements
  ASSERT_EQ_FMT(14, list1->capacity_, "%d");
  ASSERT_EQ_FMT(7, len(list1), "%d");

  // 8 bytes header + 7*4 == 8 + 28 == 36, rounded up to power of 2
  ASSERT_EQ_FMT(64, list1->slab_->cell_len_, "%d");

  ASSERT_EQ_FMT(11, list1->index(0), "%d");
  ASSERT_EQ_FMT(22, list1->index(1), "%d");
  ASSERT_EQ_FMT(33, list1->index(2), "%d");
  ASSERT_EQ_FMT(44, list1->index(3), "%d");
  ASSERT_EQ_FMT(55, list1->index(4), "%d");
  ASSERT_EQ_FMT(66, list1->index(5), "%d");
  ASSERT_EQ_FMT(77, list1->index(6), "%d");

  list1->append(88);
  ASSERT_EQ_FMT(88, list1->index(7), "%d");
  ASSERT_EQ_FMT(8, len(list1), "%d");

  int d_slab = reinterpret_cast<char*>(list1->slab_) - gHeap.from_space_;
  ASSERT(d_slab < 1024);

  log("list1_ = %p", list1);
  log("list1->slab_ = %p", list1->slab_);

  auto str1 = NewStr("foo");
  log("str1 = %p", str1);
  auto str2 = NewStr("bar");
  log("str2 = %p", str2);

  list2->append(str1);
  list2->append(str2);
  ASSERT_EQ(2, len(list2));
  ASSERT_EQ(str1, list2->index(0));
  ASSERT_EQ(str2, list2->index(1));

  // This combination is problematic.  Maybe avoid it and then just do
  // .extend({1, 2, 3}) or something?
  // https://stackoverflow.com/questions/21573808/using-initializer-lists-with-variadic-templates
  // auto list3 = gc_alloc<List<int>>({1, 2, 3});
  // auto list4 = gc_alloc<List<Str*>>({str1, str2});

  // log("len(list3) = %d", len(list3));
  // log("len(list4) = %d", len(list3));

  PASS();
}

// TODO:
// - Test set() can resize the dict
//   - I guess you have to do rehashing?

TEST dict_test() {
  auto dict1 = gc_alloc<Dict<int, int>>();
  auto dict2 = gc_alloc<Dict<Str*, Str*>>();

  ASSERT_EQ(0, len(dict1));
  ASSERT_EQ(0, len(dict2));

  ASSERT_EQ_FMT(Tag::FixedSize, dict1->tag, "%d");
  ASSERT_EQ_FMT(Tag::FixedSize, dict1->tag, "%d");

  ASSERT_EQ_FMT(0, dict1->capacity_, "%d");
  ASSERT_EQ_FMT(0, dict2->capacity_, "%d");

  ASSERT_EQ(nullptr, dict1->index_);
  ASSERT_EQ(nullptr, dict1->keys_);
  ASSERT_EQ(nullptr, dict1->values_);

  // Make sure they're on the heap
  int diff1 = reinterpret_cast<char*>(dict1) - gHeap.from_space_;
  int diff2 = reinterpret_cast<char*>(dict2) - gHeap.from_space_;
  ASSERT(diff1 < 1024);
  ASSERT(diff2 < 1024);

  dict1->set(42, 5);
  ASSERT_EQ(5, dict1->index(42));
  ASSERT_EQ(1, len(dict1));
  ASSERT_EQ_FMT(6, dict1->capacity_, "%d");

  ASSERT_EQ_FMT(32, dict1->index_->cell_len_, "%d");
  ASSERT_EQ_FMT(32, dict1->keys_->cell_len_, "%d");
  ASSERT_EQ_FMT(32, dict1->values_->cell_len_, "%d");

  dict1->set(42, 99);
  ASSERT_EQ(99, dict1->index(42));
  ASSERT_EQ(1, len(dict1));
  ASSERT_EQ_FMT(6, dict1->capacity_, "%d");

  dict1->set(43, 10);
  ASSERT_EQ(10, dict1->index(43));
  ASSERT_EQ(2, len(dict1));
  ASSERT_EQ_FMT(6, dict1->capacity_, "%d");

  for (int i = 0; i < 14; ++i) {
    dict1->set(i, 999);
    log("i = %d, capacity = %d", i, dict1->capacity_);

    // make sure we didn't lose old entry after resize
    ASSERT_EQ(10, dict1->index(43));
  }

  dict2->set(NewStr("foo"), NewStr("bar"));
  ASSERT_EQ(1, len(dict2));
  ASSERT(str_equals(NewStr("bar"), dict2->index(NewStr("foo"))));

  ASSERT_EQ_FMT(32, dict2->index_->cell_len_, "%d");
  ASSERT_EQ_FMT(64, dict2->keys_->cell_len_, "%d");
  ASSERT_EQ_FMT(64, dict2->values_->cell_len_, "%d");

  // Check other sizes

  auto dict_si = gc_alloc<Dict<Str*, int>>();
  dict_si->set(NewStr("foo"), 42);
  ASSERT_EQ(1, len(dict_si));

  ASSERT_EQ_FMT(32, dict_si->index_->cell_len_, "%d");
  ASSERT_EQ_FMT(64, dict_si->keys_->cell_len_, "%d");
  ASSERT_EQ_FMT(32, dict_si->values_->cell_len_, "%d");

  auto dict_is = gc_alloc<Dict<int, Str*>>();
  dict_is->set(42, NewStr("foo"));
  ASSERT_EQ(1, len(dict_is));

  ASSERT_EQ_FMT(32, dict_is->index_->cell_len_, "%d");
  ASSERT_EQ_FMT(32, dict_is->keys_->cell_len_, "%d");
  ASSERT_EQ_FMT(64, dict_is->values_->cell_len_, "%d");

  PASS();
}

TEST sizeof_test() {
  log("");

  // 24 = 4 + (4 + 4 + 4) + 8
  // Feels like a small string optimization here would be nice.
  log("sizeof(Str) = %d", sizeof(Str));
  // 16 = 4 + pad4 + 8
  log("sizeof(List) = %d", sizeof(List<int>));
  // 32 = 4 + pad4 + 8 + 8 + 8
  log("sizeof(Dict) = %d", sizeof(Dict<int, int>));

  // 8 byte sheader
  log("sizeof(Cell) = %d", sizeof(Cell));
  // 8 + 128 possible entries
  log("sizeof(FixedCell) = %d", sizeof(FixedCell));

  log("sizeof(Heap) = %d", sizeof(Heap));

  char* p = static_cast<char*>(Alloc(17));
  char* q = static_cast<char*>(Alloc(9));
  log("p = %p", p);
  log("q = %p", q);

  PASS();
}

class Point : public Cell {
 public:
  Point(int x, int y)
      : Cell(Tag::Opaque, kZeroMask, sizeof(Point)), x_(x), y_(y) {
  }
  int size() {
    return x_ + y_;
  }
  int x_;
  int y_;
};

const int kLineMask = 0x3;  // 0b0011
class Line : public Cell {
 public:
  Line()
      : Cell(Tag::FixedSize, kLineMask, sizeof(Line)),
        begin_(nullptr),
        end_(nullptr) {
  }
  Point* begin_;
  Point* end_;
};

TEST asdl_test() {
  auto p = Handle<Point>(gc_alloc<Point>(3, 4));
  log("point size = %d", p->size());

  auto line = Handle<Line>(gc_alloc<Line>());
  line->begin_ = p.get();  // hm .get() is annoying
  line->end_ = gc_alloc<Point>(5, 6);

  gHeap.Collect();

  // remove last reference
  line->end_ = nullptr;

  gHeap.Collect();

  // TODO: assert the heap size here!

  gHeap.Init(kInitialSize);  // reset the whole thing

  PASS();
}

void ShowRoots(const Heap& heap) {
  log("--");
  for (int i = 0; i < heap.roots_top_; ++i) {
    log("%d. %p", i, heap.roots_[i]);
    // This is NOT on the heap; it's on the stack.
    // int diff1 = reinterpret_cast<char*>(heap.roots[i]) - gHeap.from_space_;
    // assert(diff1 < 1024);

    auto h = static_cast<Handle<void>*>(heap.roots_[i]);
    auto raw = h->raw_pointer_;
    log("   %p", raw);

    // Raw pointer is on the heap.
    int diff2 = reinterpret_cast<char*>(raw) - gHeap.from_space_;
    // log("diff2 = %d", diff2);
    assert(diff2 < 2048);

    // This indeed mutates it and causes a crash
    // h->update(nullptr);
  }
}

Str* myfunc() {
  HandleScope h(3);
  Handle<Str> str1(NewStr("foo"));
  Handle<Str> str2(NewStr("foo"));
  Handle<Str> str3(NewStr("foo"));

  log("myfunc roots_top = %d", gHeap.roots_top_);
  ShowRoots(gHeap);

  return str1.raw_pointer_;
}

void otherfunc(Handle<Str> s) {
  // Hm how do we generate the .get()?  Is it better just to accept Handle<Str>
  // even if the function doesn't allocate?  Either way we are dereferencing.
  log("len(s) = %d", len(s));
}

TEST handle_test() {
  // TODO:
  // Hold on to a handle.  And then trigger GC.
  // And then assert its integrity?

  {
    HandleScope h(2);
    log("top = %d", gHeap.roots_top_);
    ASSERT_EQ(0, gHeap.roots_top_);

    auto point = gc_alloc<Point>(3, 4);
    Handle<Point> p(point);
    ASSERT_EQ(1, gHeap.roots_top_);

    log("point.x = %d", p->x_);    // invokes operator->
    log("point.y = %d", (*p).y_);  // invokes operator* I think

    Handle<Str> str2(NewStr("bar"));
    ASSERT_EQ(2, gHeap.roots_top_);

    myfunc();

    otherfunc(str2);

    ShowRoots(gHeap);

    gHeap.Collect();
  }
  ASSERT_EQ_FMT(0, gHeap.roots_top_, "%d");

  PASS();
}

// TODO: the last one overflows
int sizes[] = {0, 1,  2,  3,   4,   5,       8,
               9, 12, 16, 256, 257, 1 << 30, (1 << 30) + 1};
int nsizes = sizeof(sizes) / sizeof(sizes[0]);

TEST resize_test() {
  for (int i = 0; i < nsizes; ++i) {
    int n = sizes[i];
    log("%d -> %d", n, RoundUp(n));
  }

  PASS();
}

void ShowFixedChildren(FixedCell* fixed) {
  log("MASK:");

  // Note: can this be optimized with the equivalent x & (x-1) trick?
  // We need the index
  // There is a de Brjuin sequence solution?
  // https://stackoverflow.com/questions/757059/position-of-least-significant-bit-that-is-set

  int mask = fixed->field_mask_;
  for (int i = 0; i < 16; ++i) {
    if (mask & (1 << i)) {
      Cell* child = fixed->children_[i];
      // make sure we get Tag::Opaque, Tag::Scanned, etc.
      log("i = %d, p = %p, tag = %d", i, child, child->tag);
    }
  }
}

void ShowSlab(Cell* cell) {
  assert(cell->tag == Tag::Scanned);
  auto slab = reinterpret_cast<Slab<void*>*>(cell);

  // Scan until we hit nullptr.
  // I think this should work for dictionaries too, because the entries should
  // be dense?  What about deletions?
  //
  // Maybe we need Tag::DenseScannedSlab and Tag::SparseScannedSlab ?
  // The difference should only be a factor of 2 though.

  int n = (slab->cell_len_ - kSlabHeaderSize) / sizeof(void*);
  log("slab len = %d, n = %d", slab->cell_len_, n);
  for (int i = 0; i < n; ++i) {
    void* p = slab->items_[i];
    if (p == nullptr) {
      break;
    }
    log("p = %p", p);
  }
}

TEST field_mask_test() {
  auto L = gc_alloc<List<int>>();
  L->append(1);
  log("List mask = %d", L->field_mask_);

  auto d = gc_alloc<Dict<Str*, int>>();
  d->set(NewStr("foo"), 3);
  log("Dict mask = %d", d->field_mask_);

  auto L_cell = reinterpret_cast<FixedCell*>(L);
  ShowFixedChildren(L_cell);

  auto d_cell = reinterpret_cast<FixedCell*>(d);
  ShowFixedChildren(d_cell);

  auto L2 = gc_alloc<List<Str*>>();
  auto s = NewStr("foo");
  L2->append(s);
  L2->append(s);
  ShowSlab(L2->slab_);
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  // Should be done once per thread
  gHeap.Init(kInitialSize);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(str_test);
  RUN_TEST(list_test);
  RUN_TEST(dict_test);
  RUN_TEST(sizeof_test);
  RUN_TEST(asdl_test);
  RUN_TEST(handle_test);
  RUN_TEST(resize_test);
  RUN_TEST(field_mask_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
