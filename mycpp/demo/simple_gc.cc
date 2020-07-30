// Simplest garbage collector that will work.
//
// It's a semi-space collector.  (Later we could add a "large object space",
// managed by mark-and-sweep after each copy step.)
//
// Design:
// - Immutable Slab, Sheet, and Str
// - Mutable List, Dict that point to Slab/Sheet
//
// TODO:
// - Prototype RootPtr<T> for stack roots
//   - and I guess PtrScope() or something
//
// - List.append() can realloc
// - Dict.set() can realloc
//
// - GLOBAL Str* instances should not be copied!
//   - do they have a special Cell header?
//     - special tag?
//   - can they be constexpr?

// APIs:
// - gc_alloc<Foo>(x): an alternative to new Foo(x).  for generated code like
//   mycpp/ASDL to use.  Automatically deallocated.
// - mylib::Alloc() -- for Slab and Sheet, and for special types like
//   Str.  Automatically deallocated.
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
    how_t cell_len_;  // # bytes to copy, or # bytes to scan?
    how_t field_mask; // last 1 bit determines length
                      // so maximum 31 fields?
  };
};

class Forwarded : public Cell {
  // only valid if tag == Tag::Forwarded
  Cell* new_location;
};

// Opaque slab.  e.g. for String data
class Slab : public Cell {
 public:
  Slab() 
      : opaque_("") {
  }
  int capacity_;
  char opaque_[1];  // minimum string cell_len_
};

// Building block for Dict and List.  Or is this List itself?
// Note: it's not managed with 'new'?
class Sheet : public Cell {
 public:
  int capacity_;
  Cell* pointers_[1];  // minimum List<Str*> cell_len_
};

// NOT USED.  This object is too big, and it complicates the GC.
class Slice : public Cell {
 public:
  Slice(Slab* slab, int begin, int end)
      : begin_(begin), end_(end), slab_(slab) {
  }
  int begin_;
  int end_;
  int hash_;
  // Note: later this can be an atom_id
  Slab* slab_;
};

class Str : public Cell {
 public:
  int len_;
  int unique_id_;  // index into intern table
  char opaque_[1];  // flexible array
};

void PrintSlice(Slice* s) {
  char* data = s->slab_->opaque_;
  char* p = data + s->begin_;
  fwrite(p, 1, s->end_ - s->begin_, stdout);
  puts("");
}

template <class T>
class List : public Cell {
 public:
  List() : len_(0) {
    // TODO: initial slab?
  }

  List(std::initializer_list<T> init) {
    // TODO: allocate a new slab with the right size?
    // Rather than "aligning", it needs to be Sized()
    // Rather than Alloc(), maybe it's ReAlloc() ?  That encapsulates our size
    // policy.
    //
    // ReAlloc(int size)
    // ReAlloc(Slab* slab)  // reads capacity from either
    // ReAlloc(Sheet* slab)
    //
    // How do you specialize Sheet or Slab?

    for (T item : init) {
      //v_.push_back(item);
    }
  }

  void append(T item) {
    // TODO: check the Slab/Sheet capacity
    // If it's full, then Alloc() another slab, then memcpy()
    // The old one will be cleaned up by GC.
    assert(0);
  }

  void extend(std::initializer_list<T> init) {
    int n = init.size();
    log("init.size() = %d", n);
    for (T item : init) {
      log("T");
    }
    len_ += n;
  }

  int len_;  // container length

  // This sequence may be resized, so it's not in-line.
  union {
    Slab* slab;  // List<int>
    Sheet* sheet;  // List<Str*>
  };
};

template <class K, class V>
class Dict : public Cell {
 public:
  void set(K key, V value) {
    // may resize the dictionary
    assert(0);
  }

  int len_;  // container length

  // These 3 sequences may be resized "in parallel"

  Slab* indices;  // indexed by hash value
  union {
    Slab* keys_slab;  // Dict<int, V>
    Sheet* keys_sheet;  // Dict<Str*, V>
  };
  union {
    Slab* values_slab;  // Dict<K, int>
    Sheet* values_sheet;  // Dict<K, Str*>
  };
};

//
// "Constructors"
//

// Note: This is NewStr() because of the "flexible array" pattern.
// I don't think "new Str()" can do that, and placement new would require mycpp
// to generate 2 statements everywhere.

Str* NewStr(const char* data, int len) {
  // subtract opaque[1].  Alloc() does the alignment.
  void* p = Alloc(sizeof(Str) - 1 + len);  // allocate exactly the right amount

  Str* s = static_cast<Str*>(p);
  s->SetCellLength(len);  // is this right?
  s->len_ = len;
  memcpy(s->opaque_, data, len);

  return s;
}

Str* NewStr(const char* data) {
  return NewStr(data, strlen(data));
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
  auto slab1 = new Slab();

  auto slice1 = new Slice(slab1, 2, 5);

  PrintSlice(slice1);

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
// - Test that it's on the gcHeap
// - Test append() creating a new sheet/slab
// - Test Sheet vs. slab: List<int> vs. List<Str*>
// - Test what happens append() runs over the max heap size
//   - how does it trigger a collection?

TEST list_test() {
  auto list1 = gc_alloc<List<int>>();
  auto list2 = gc_alloc<List<Str*>>();

  log("len(list1) = %d", len(list1));
  log("len(list2) = %d", len(list2));

  list1->extend({1,2,3});
  log("len(list1) = %d", len(list1));

  auto str1 = NewStr("foo");
  auto str2 = NewStr("bar");

  // This combination is problematic.  Maybe avoid it and then just do
  // .extend({1, 2, 3}) or something?
  // https://stackoverflow.com/questions/21573808/using-initializer-lists-with-variadic-templates
  //auto list3 = gc_alloc<List<int>>({1, 2, 3});
  //auto list4 = gc_alloc<List<Str*>>({str1, str2});

  //log("len(list3) = %d", len(list3));
  //log("len(list4) = %d", len(list3));

  // Make sure they're on the heap
  int diff1 = reinterpret_cast<char*>(list1) - gHeap.from_space_;
  int diff2 = reinterpret_cast<char*>(list2) - gHeap.from_space_;
  ASSERT(diff1 < 1024);
  ASSERT(diff2 < 1024);

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
