// mycpp/gc_heap.h
//
// A garbage collected heap that looks like statically typed Python: Str,
// List<T>, Dict<K, V>.

#ifndef GC_HEAP_H
#define GC_HEAP_H

#include <cassert>  // assert()
#include <cstdlib>  // malloc
#include <cstring>  // memcpy
#include <initializer_list>
#include <new>      // placement new
#include <utility>  // std::forward

#include "mycpp/common.h"

// Design Notes:

// It's a semi-space collector using the Cheney algorithm.  (Later we may add a
// "large object space", managed by mark-and-sweep after each copy step.)

// Influences / Prior art:
//
// - OCaml / ZINC machine - statically typed, everything is a pointer (no value
//   types).
// - femtolisp - Cheney collector; used to bootstrap Juliia.
// - Other: ES shell, Lua, Python and especially Python dicts.

// Design:
//
// - Graph of application types:
//   - Str*
//   - List<T>*
//   - Dict<K, V>*
//   - User-defined classes, which may have a vtable pointer.
// - Graph of GC nodes: everything is an Obj* with an 8 byte header
//   - 1 byte heap tag, for Cheney
//   - 1 byte type tag for Zephyr ASDL unions
//   - 2 byte / 16-bit field bit mask for following pointers on user-defined
//     classes and List / Dict "headers"
//   - 4 bytes length for Cheney to determine how much to copy.
//
// Operations that resize:
//
// - List::append() and extend() can realloc
// - Dict::set() can realloc and rehash (TODO)
//
// Important Types:
//
// - Slab<T> to trace the object graph.  Slab<int> is opaque, but Slab<T*>
//   requires tracing.
//   - A List<T> is a fixed-size structure, with int fields and a pointer
//     to a single Slab<T> (the items).
//   - A Dict<K, V> is also fixed-size, with pointers to 3 slabs: the index
//     Slab<int>, the keys Slab<K>, and the index Slab<V>.
//
// "Ghost" layout types:
//
// - LayoutFixed - for walking up to 16 fields of a user-defined type.
// - LayoutForwarded - for storing the forwarding pointer that the Cheney
//   algorithm uses.
//
// Stack rooting API:
//
//   StackRoots _roots({&mystr, &mydict, &mylist});
//
// This pushes local variables onto the global data structure managed by the
// GC.

// TODO: Dicts should actually use hashing!  Test computational complexity.

// Memory allocation APIs:
//
// - Alloc<Foo>(x)
//   The typed public API.  An alternative to new Foo(x).  mycpp/ASDL should
//   generate these calls.
// - AllocStr(length), StrFromC(), NewList, NewDict: Alloc() doesn't
// work
//   for these types for various reasons
// - Heap::Allocate()
//   The untyped internal API.  For AllocStr() and NewSlab().
// - malloc() -- for say yajl to use.  Manually deallocated.
// - new/delete -- shouldn't be in Oil?

// Slab Sizing with 8-byte slab header
//
//   16 - 8 =  8 = 1 eight-byte or  2 four-byte elements
//   32 - 8 = 24 = 3 eight-byte or  6 four-byte elements
//   64 - 8 = 56 = 7 eight-byte or 14 four-byte elements

// #defines for degbugging:
//
// GC_EVERY_ALLOC: Collect() on every Allocate().  Exposes many bugs!
// GC_VERBOSE: Log when we collect
// GC_STATS: Collect more stats.  TODO: Rename this?

// Silly definition for passing types like GlobalList<T, N> and initializer
// lists like {1, 2, 3} to macros

template <class T>
class List;

class Obj;

const int kMaxRoots = 4 * 1024;  // related to C stack size

class Space {
 public:
  Space() {
  }
  void Init(int space_size);

  void Free();

#if GC_STATS
  void AssertValid(void* p) {
    if (begin_ <= p && p < begin_ + size_) {
      return;
    }
    log("p = %p isn't between %p and %p", begin_, begin_ + size_);
    InvalidCodePath();
  }
#endif

  char* begin_;
  int size_;  // number of bytes
};

class Heap {
 public:
  Heap() {  // default constructor does nothing -- relies on zero initialization
  }

  // Real initialization with the initial heap size.  The heap grows with
  // allocations.
  void Init(int space_size) {
    // malloc() and memset()
    from_space_.Init(space_size);
    /* to_space_.Init(space_size); */

    free_ = from_space_.begin_;  // where we allocate from
    limit_ = free_ + space_size;

    roots_top_ = 0;

    is_initialized_ = true;

#if GC_STATS
    num_collections_ = 0;
    num_heap_growths_ = 0;
    num_forced_growths_ = 0;
    num_live_objs_ = 0;
#endif
  }

  void* Bump(int n) {
    char* p = free_;
    free_ += n;
#if GC_STATS
    num_live_objs_++;
#endif
    return p;
  }

  void* Allocate(int num_bytes) {
    int n = aligned(num_bytes);
    // log("n = %d, p = %p", n, p);

    // TODO(Jesse): Change to `assert(n >= sizeof(LayoutForwarded))`
    //
    // This must be at least sizeof(LayoutForwarded), which happens to be 16
    // bytes, because the GC pointer forwarding requires 16 bytes.  If we
    // allocated less than 16 the GC would overwrite the adjacent object when
    // it went to forward the pointer.
    assert(n >= 16);

#if GC_EVERY_ALLOC
    Collect();  // force collection to find problems early
#endif

    if (free_ + n <= limit_) {  // Common case: we have space for it.
      return Bump(n);
    }

#if GC_STATS
      // log("GC free_ %p,  from_space_ %p, space_size_ %d", free_, from_space_,
      //    space_size_);
#endif

    Collect();  // Try to free some space.

    // log("after GC: from begin %p, free_ %p,  n %d, limit_ %p",
    //    from_space_.begin_, free_, n, limit_);

    if (free_ + n <= limit_) {  // Now we have space for it.
      return Bump(n);
    }

    // It's still too small.  Grow the heap.
    int multiple = 2;
    Collect((from_space_.size_ + n) * multiple);

#if GC_STATS
    num_forced_growths_++;
#endif

    return Bump(n);
  }

  void Swap() {
    // Swap spaces for next collection.
    char* tmp = from_space_.begin_;
    from_space_.begin_ = to_space_.begin_;
    to_space_.begin_ = tmp;

    int tmp2 = from_space_.size_;
    from_space_.size_ = to_space_.size_;
    to_space_.size_ = tmp2;
  }

  void PushRoot(Obj** p) {
    // log("PushRoot %d", roots_top_);
    roots_[roots_top_++] = p;
    // TODO: This should be like a malloc() failure?
    assert(roots_top_ < kMaxRoots);
  }

  void PopRoot() {
    roots_top_--;
    // log("PopRoot %d", roots_top_);
  }

  Obj* Relocate(Obj* obj, Obj* header);

  // mutates free_ and other variables
  void Collect(int to_space_size = 0);

#if GC_STATS
  void Report() {
    log("-----");
    log("num collections = %d", num_collections_);
    log("num heap growths = %d", num_heap_growths_);
    log("num forced heap growths = %d", num_forced_growths_);
    log("num live objects = %d", num_live_objs_);

    log("from_space_ %p", from_space_.begin_);
    log("to_space %p", to_space_.begin_);
    log("-----");
  }
#endif

  Space from_space_;  // space we allocate from
  Space to_space_;    // space that the collector copies to

  char* free_;   // next place to allocate, from_space_ <= free_ < limit_
  char* limit_;  // end of space we're allocating from

  // Stack roots.  The obvious data structure is a linked list, but an array
  // has better locality.
  //
  // femtolisp uses a global pointer to dynamically-allocated growable array,
  // with initial N_STACK = 262144!  Kind of arbitrary.

  int roots_top_;
  Obj** roots_[kMaxRoots];  // These are pointers to Obj* pointers

  bool is_initialized_ = false;

#if GC_STATS
  int num_collections_;
  int num_heap_growths_;
  int num_forced_growths_;  // when a single allocation is too big
  int num_live_objs_;
#endif
};

// The heap is a (compound) global variable.  Notes:
// - The default constructor does nothing, to avoid initialization order
//   problems.
// - For some applications, this can be thread_local rather than global.
extern Heap gHeap;

class StackRoots {
 public:
  StackRoots(std::initializer_list<void*> roots) {
    n_ = roots.size();
    for (auto root : roots) {  // can't use roots[i]
      gHeap.PushRoot(reinterpret_cast<Obj**>(root));
    }
  }

  ~StackRoots() {
    // TODO: optimize this
    for (int i = 0; i < n_; ++i) {
      gHeap.PopRoot();
    }
  }

 private:
  int n_;
};

#if GC_STATS
void ShowFixedChildren(Obj* obj);
#endif

// Obj::heap_tag_ values.  They're odd numbers to distinguish them from vtable
// pointers.
//
// NOTE(Jesse): Changed to an enum because namespaces can't be typedef'd.
// ie can't be included using the 'using' keyword
//
enum Tag {
  Forwarded = 1,  // For the Cheney algorithm.
  Global = 3,     // Neither copy nor scan.
  Opaque = 5,     // Copy but don't scan.  List<int> and Str
  FixedSize = 7,  // Fixed size headers: consult field_mask_
  Scanned = 9,    // Copy AND scan for non-NULL pointers.
};

const int kZeroMask = 0;  // for types with no pointers
// no obj_len_ computed for global List/Slab/Dict
const int kNoObjLen = 0x0eadbeef;

// Why do we need this macro instead of using inheritance?
// - Because ASDL uses multiple inheritance for first class variants, but we
//   don't want multiple IMPLEMENTATION inheritance.  Instead we just generate
//   compatible layouts.
// - Similarly, GlobalStr is layout-compatible with Str.  It can't inherit from
//   Obj like Str, because of the constexpr issue with char[N].

// heap_tag_: one of Tag::
// type_tag_: ASDL tag (variant)
// field_mask_: for fixed length records, so max 16 fields
// obj_len_: number of bytes to copy
//   TODO: with a limitation of ~15 fields, we can encode obj_len_ in
//   field_mask_, and save space on many ASDL types.
//   And we can sort integers BEFORE pointers.

// TODO: ./configure could detect big or little endian, and then flip the
// fields in OBJ_HEADER?
//
// https://stackoverflow.com/questions/2100331/c-macro-definition-to-determine-big-endian-or-little-endian-machine
//
// Because we want to do (obj->heap_tag_ & 1 == 0) to distinguish it from
// vtable pointer.  We assume low bits of a pointer are 0 but not high bits.

#define OBJ_HEADER()    \
  uint8_t heap_tag_;    \
  uint8_t type_tag_;    \
  uint16_t field_mask_; \
  uint32_t obj_len_;

class Obj {
  // The unit of garbage collection.  It has a header describing how to find
  // the pointers within it.
  //
  // Note: Sorting ASDL fields by (non-pointer, pointer) is a good idea, but it
  // breaks down because mycpp has inheritance.  Could do this later.

 public:
  // Note: ASDL types are layout-compatible with Obj, but don't actually
  // inherit from it because of the 'multiple inheritance of implementation'
  // issue.  So they don't call this constructor.
  constexpr Obj(uint8_t heap_tag, uint16_t field_mask, int obj_len)
      : heap_tag_(heap_tag),
        type_tag_(0),
        field_mask_(field_mask),
        obj_len_(obj_len) {
  }

  void SetObjLen(int obj_len) {
    this->obj_len_ = obj_len;
  }

  OBJ_HEADER()

  DISALLOW_COPY_AND_ASSIGN(Obj)
};

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

// Variadic templates:
// https://eli.thegreenplace.net/2014/variadic-templates-in-c/
template <typename T, typename... Args>
T* Alloc(Args&&... args) {
  assert(gHeap.is_initialized_);

#ifdef MARK_SWEEP
  void* place = calloc(sizeof(T), 1);  // make sure it's set to zero

  // TODO:
  // - trace, sweep, and free()
  // - collection policy: every N allocations?

#else
  void* place = gHeap.Allocate(sizeof(T));
#endif
  assert(place != nullptr);
  // placement new
  return new (place) T(std::forward<Args>(args)...);
}

#endif  // GC_HEAP_H
