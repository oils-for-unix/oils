// Simplest garbage collector that will work.
//
// It's a semi-space collector.  (Later we could add a "large object space",
// managed by mark-and-sweep after each copy step.)
//
// TODO:
// - Immutable Slab, Sheet, and Str
// - Mutable List, Dict that point to Slab/Sheet
//
// - Prototype RootPtr<T> for stack roots
//   - and I guess PtrScope() or something
//
// - List.append() can realloc
// - Hook up alloactors.  new()?
//   - but Slab and Sheet can't use that.
//
// - GLOBAL Str* instances should not be copied!
//   - do they have a special Cell header?
//     - special tag?
//   - can they be constexpr?


// APIs:
// - new: for generated code like mycpp/ASDL to use.  Because of the typing
//   issue?  Automatically deallocated.
//
// - malloc() -- for say yajl to use.  It frees its own memory
//
// - mylib::Alloc() -- for internal data structures and operator new() to use
//                     Automatically deallocated

#include <cassert>  // assert()
#include <cstdarg>  // va_list, etc.
#include <cstdio>   // vprintf
#include <cstdint>  // max_align_t
#include <cstring>  // memcpy
#include <cstdlib>  // malloc
#include <cstddef>  // max_align_t

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

  char alloc_pos_;

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
      : opaque_("foobar") {
  }
  char opaque_[8];  // minimum string cell_len_
};

// Building block for Dict and List.  Or is this List itself?
// Note: it's not managed with 'new'?
class Sheet : public Cell {
 public:
  Cell* pointers_[4];  // minimum List<Str*> cell_len_
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
  void append(T item) {
    // TODO: check the capacity
    // If it's full, then Alloc() another slab, then memcpy()
    // The old one will be cleaned up by GC.
    assert(0);
  }

  int len_;  // container length
  union {
    Slab* slab;  // List<int>
    Sheet* sheet;  // List<Str*>
  };
};

template <class K, class V>
class Dict : public Cell {
 public:
  int len_;  // container length
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

// TODO:
// What about ASDL types?
//
// Token* tok = alloc<Token>(id, val);
//
// Does this cause code bloat?

Str* NewStr(const char* data, int len) {
  void* p = Alloc(len);  // allocate exactly the right amount

  Str* s = static_cast<Str*>(p);
  s->SetCellLength(len);  // is this right?
  s->len_ = len;
  memcpy(s->opaque_, data, len);

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

int main(int argc, char** argv) {
  // Should be done once per thread
  InitHeap();

  // hm this shouldn't be allocated with 'new'
  // it needs a different interface
  auto slab1 = new Slab();

  auto slice1 = new Slice(slab1, 2, 5);

  PrintSlice(slice1);

  auto str1 = NewStr("");

  //auto str2 = new Str("buffer overflow?");
  //auto str2 = new Str("food");

  log("");
  log("len(str1) = %d", len(str1));
  //log("len(str2) = %d", len(str2));

  auto list1 = new List<int>();
  auto list2 = new List<Str*>();

  log("len(list1) = %d", len(list1));
  log("len(list2) = %d", len(list2));

  auto dict1 = new Dict<int, int>();
  auto dict2 = new Dict<Str*, Str*>();

  log("len(dict1) = %d", len(dict1));
  log("len(dict2) = %d", len(dict2));

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
}
