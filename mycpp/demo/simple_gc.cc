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
// - Prototype RootPtr<T> for stack roots
//   - and I guess PtrScope() or something
//
// - GLOBAL Str* instances should not be copied!
//   - do they have a special Cell header?
//     - special tag?
//   - can they be constexpr?

// Memory allocation APIs:
//
// - gc_alloc<Foo>(x)
//   An alternative to new Foo(x).  mycpp/ASDL should generate these calls.
//   Automatically deallocated.
// - mylib::Alloc() 
//   For Slab, and for special types like Str.  Automatically deallocated.
// - malloc() -- for say yajl to use.  Manually deallocated.
// - new/delete -- for other C++ libs to use.  Manually deallocated.

#include <cassert>  // assert()
#include <cstdarg>  // va_list, etc.
#include <cstdio>   // vprintf
#include <cstdint>  // max_align_t
#include <cstring>  // memcpy
#include <cstdlib>  // malloc
#include <cstddef>  // max_align_t
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

// handles get registered here, and they appear on the heap somehow
class HandleScope {
};

// behaves like a pointer
class Handle {
};


struct Heap {
  char* from_space_;
  char* to_space_;

  int alloc_pos_;

  // how to represent this?
  // femtolisp uses a global pointer to dynamically-allocated growable array,
  // with initial N_STACK = 262144!  Kind of arbitrary.
  void* root_pointers[100];

  // scan pointer, next pointer

  // reallocation policy?
};

// TODO: Make this a thread local?
Heap gHeap;

// 1 MiB, and will double when necessary
const int kInitialSize = 1 << 20;

void InitHeap() {
  gHeap.from_space_ = static_cast<char*>(malloc(kInitialSize));
  gHeap.to_space_ = static_cast<char*>(malloc(kInitialSize));
  gHeap.alloc_pos_ = 0;

#if GC_DEBUG
  // TODO: make it 0xdeadbeef
  memset(gHeap.from_space_, 0xff, kInitialSize);
  memset(gHeap.to_space_, 0xff, kInitialSize);
#endif
}

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

// Variadic templates
// https://eli.thegreenplace.net/2014/variadic-templates-in-c/
template<typename T, typename... Args>
T *gc_alloc(Args&&... args)
{
  void* place = Alloc(sizeof(T));

  // placement new
  return new (place) T(std::forward<Args>(args)...);
}

// Return the size of a resizeable allocation.  For now we just round up by
// powers of 2. This could be optimized later.  CPython has an interesting
// policy in listobject.c.
//
// https://stackoverflow.com/questions/466204/rounding-up-to-next-power-of-2
int NewBlockSize(int n) {
  // minimum size
  if (n < 4) {
    return 4;
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

// TODO: Do copying collection.
// What's the resizing policy?
void CollectGarbage() {
}

namespace Tag {
  const int Forwarded = 1;
}

// This forces an 8-byte Cell header.  It's better not to have special cases
// like the "how_index" at first.
//
// It may be possible to enforce a limit of 2^24 = 16 MiB on strings and
// arrays.  But let's treat that as an optimization for later.
//
// We don't want to break code like x=$(cat big_file)
typedef uint32_t how_t;

class Cell {
  // The unit of garbage collection.  It has a header describing how to find
  // the pointers within it.
  //
  // (Note: sorting ASDL fields by (non-pointer, pointer) is a good idea, but
  //  it breaks down because mycpp has inheritance.  Could do this later.)

 public:
  Cell() : tag(0), cell_len_(0) {
  }
  Cell(int tag) : tag(tag), cell_len_(0) {
  }

  void SetCellLength(int len) {
    this->cell_len_ = cell_len_;
  }

  uint16_t tag;  // ASDL tags are 0 to 255
                 // Tag::Forwarded is 256?
                 // We could also reserve tags for Str, List, and Dict
                 // Then do we have 7 more bits for the GC strategy / length?

  // How to trace fields in this object.
  union {
    // # bytes to copy, or # bytes to scan?
    // for Slab, which is used by List<Str*> and Dict<Str*, Str*>
    how_t cell_len_;
    how_t field_mask; // last 1 bit determines length
                      // so maximum 31 fields?
  };
};

class Forwarded : public Cell {
  // only valid if tag == Tag::Forwarded
  Cell* new_location;
};

// Opaque slab.  e.g. for String data
template <typename T>
class Slab : public Cell {
 public:
  Slab(int capacity) : capacity_(capacity) {
  }
  int capacity_;
  T items_[1];  // minimum string cell_len_
};

// don't include items_[1]
const int kSlabHeaderSize = sizeof(Cell) + sizeof(int);

template <typename T>
Slab<T>* NewSlab(int capacity) {
  int cell_len = kSlabHeaderSize + capacity;
  void* place = Alloc(cell_len);
  auto slab = new (place) Slab<T>(capacity);  // placement new
  slab->SetCellLength(capacity);
  return slab;
}

// NOT USED.  This object is too big, and it complicates the GC.
class Slice : public Cell {
 public:
  Slice(Slab<int>* slab, int begin, int end)
      : begin_(begin), end_(end), slab_(slab) {
  }
  int begin_;
  int end_;
  int hash_;
  // Note: later this can be an atom_id
  Slab<int>* slab_;
};

class Str : public Cell {
 public:
  // Note: shouldn't be called directly.  Call NewStr().
  Str(int len) : len_(len) {
  }
  int len_;
  int unique_id_;  // index into intern table
  char opaque_[1];  // flexible array
};

const int kStrHeaderSize = sizeof(Cell) + sizeof(int) + sizeof(int);


#if 0
void PrintSlice(Slice* s) {
  char* data = s->slab_->opaque_;
  char* p = data + s->begin_;
  fwrite(p, 1, s->end_ - s->begin_, stdout);
  puts("");
}
#endif

template <class T>
class List : public Cell {
 public:
  List() : len_(0), slab_(nullptr) {
  }

  List(std::initializer_list<T> init) {
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

  // Ensure that there's space for a number of items
  void reserve(int n) {
    // TODO: initialize in constructor?  But many lists are empty!
    if (slab_ == nullptr) {
      int capacity = NewBlockSize(n * sizeof(T));
      void* place = Alloc(kSlabHeaderSize + capacity);
      slab_ = new (place) Slab<T>(capacity);  // placement new

    } else if (len_ + n >= slab_->capacity_) {
      int new_len = len_ + n;
      int new_cap = NewBlockSize(new_len * sizeof(T));
      void* place = Alloc(kSlabHeaderSize + new_cap);
      auto new_slab = new (place) Slab<T>(new_cap);
      //log("Copying %d bytes", len_ * sizeof(T));
      memcpy(new_slab->items_, slab_->items_, len_ * sizeof(T));
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

  int len_;  // container length

  // The container may be resized, so this field isn't in-line.
  Slab<T>* slab_;
};


template <typename K, typename V>
int find_by_key(Slab<K>* keys_slab_, Slab<V>* values_slab_, int len, int key) {
  assert(0);

  // TODO: linear search for key up to "len" entries, then return i

#if 0 
  int n = items.size();
  for (int i = 0; i < n; ++i) {
    if (items[i].first == key) {
      return i;
    }
  }
  return -1;
#endif
}

template <class K, class V>
class Dict : public Cell {
 public:
  Dict() : len_(0), keys_slab_(nullptr), values_slab_(nullptr) {
  }

  void reserve(int n) {
    if (keys_slab_ == nullptr) {
      int capacity = NewBlockSize(n);
      assert(values_slab_ == nullptr);

      keys_slab_ = NewSlab<K>(capacity);
      values_slab_ = NewSlab<V>(capacity);

    } else if (keys_slab_->capacity_ < n) {
      // TODO: resize and REHASH every entry.
      assert(0);

    }
  }

  // d[key] in Python: raises KeyError if not found
  V index(K key) {
    int pos = find(key);
    if (pos == -1) {
      assert(0);
    } else {
      return values_slab_->items_[pos];
    }
  }

  // Implements d[k] = v.  May resize the dictionary.
  void set(K key, V value) {
    reserve(len_ + 1);

    int i = find_by_key(key);

    // TODO: rehashing
    assert(0);
  }

  int len_;  // container length

  // These 3 sequences may be resized "in parallel"

  Slab<int>* indices;  // indexed by hash value
  Slab<K>* keys_slab_;  // Dict<int, V>
  Slab<V>* values_slab_;  // Dict<K, int>

 private:
  // returns the position in the array
  int find(K key) {
    return find_by_key(keys_slab_, values_slab_, len_, key);
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

int len(const Str* s) {
  return s->len_;
}

template <typename T>
int len(const List<T>* L) {
  return L->len_;
}

template <typename K, typename V>
inline int len(const Dict<K, V>* d) {
  return d->len_;
}

//
// main
//

TEST slice_test() {
  // hm this shouldn't be allocated with 'new'
  // it needs a different interface
#if 0
  auto slab1 = new Slab();
  auto slice1 = new Slice(slab1, 2, 5);
  PrintSlice(slice1);
#endif

  PASS();
}

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

  // Make sure they're on the heap
  int diff1 = reinterpret_cast<char*>(list1) - gHeap.from_space_;
  int diff2 = reinterpret_cast<char*>(list2) - gHeap.from_space_;
  ASSERT(diff1 < 1024);
  ASSERT(diff2 < 1024);

  list1->extend({11, 22, 33});
  ASSERT_EQ_FMT(3, len(list1), "%d");

  ASSERT_EQ_FMT(11, list1->index(0), "%d");
  ASSERT_EQ_FMT(22, list1->index(1), "%d");
  ASSERT_EQ_FMT(33, list1->index(2), "%d");

  list1->extend({44, 55, 66, 77});
  ASSERT_EQ_FMT(7, len(list1), "%d");

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
  //auto list3 = gc_alloc<List<int>>({1, 2, 3});
  //auto list4 = gc_alloc<List<Str*>>({str1, str2});

  //log("len(list3) = %d", len(list3));
  //log("len(list4) = %d", len(list3));

  PASS();
}

// TODO:
// - Test set() can resize the dict
//   - I guess you have to do rehashing?

TEST dict_test() {
  auto dict1 = gc_alloc<Dict<int, int>>();
  auto dict2 = gc_alloc<Dict<Str*, Str*>>();

  log("len(dict1) = %d", len(dict1));
  log("len(dict2) = %d", len(dict2));

  // Make sure they're on the heap
  int diff1 = reinterpret_cast<char*>(dict1) - gHeap.from_space_;
  int diff2 = reinterpret_cast<char*>(dict2) - gHeap.from_space_;
  ASSERT(diff1 < 1024);
  ASSERT(diff2 < 1024);

  log("");

  // 24 = 4 + (4 + 4 + 4) + 8
  // Feels like a small string optimization here would be nice.
  log("sizeof(Str) = %d", sizeof(Str));
  // 16 = 4 + pad4 + 8
  log("sizeof(List) = %d", sizeof(List<int>));
  // 32 = 4 + pad4 + 8 + 8 + 8
  log("sizeof(Dict) = %d", sizeof(Dict<int, int>));

  char* p = static_cast<char*>(Alloc(17));
  char* q = static_cast<char*>(Alloc(9));
  log("p = %p", p);
  log("q = %p", q);

  PASS();
}

class Point {
 public:
  Point(int x, int y) : x_(x), y_(y) {
  }
  int size() {
    return x_ + y_;
  }
  int x_;
  int y_;
};

TEST asdl_test() {
  auto p = gc_alloc<Point>(3, 4);
  log("point size = %d", p->size());
  PASS();
}

TEST handle_test() {
  // TODO:
  // Hold on to a handle.  And then trigger GC.
  // And then assert its integrity?

  PASS();
}

// TODO: the last one overflows
int sizes[] = {0, 1, 2, 3, 4, 5, 8, 9, 12, 16, 256, 257, 1 << 30, (1 << 30)+1};
int nsizes = sizeof(sizes) / sizeof(sizes[0]);

TEST resize_test() {
  for (int i = 0; i < nsizes; ++i) {
    int n = sizes[i];
    log("%d -> %d", n, NewBlockSize(n));
  }

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  // Should be done once per thread
  InitHeap();

  GREATEST_MAIN_BEGIN();

  // don't need this for now
  RUN_TEST(slice_test);

  RUN_TEST(str_test);
  RUN_TEST(list_test);
  RUN_TEST(dict_test);
  RUN_TEST(asdl_test);
  RUN_TEST(handle_test);
  RUN_TEST(resize_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
