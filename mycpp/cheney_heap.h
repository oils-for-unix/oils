// mycpp/cheney_heap.h
//
// A garbage collected heap that looks like statically typed Python: Str,
// List<T>, Dict<K, V>.

#ifndef CHENEY_HEAP_H
#define CHENEY_HEAP_H

#include <assert.h>  // assert()
#include <stdlib.h>  // malloc()
#include <string.h>  // memcpy()

#include <initializer_list>

#include "mycpp/common.h"

#undef MARK_SWEEP  // TODO: put this in the build system

struct ObjHeader;  // from gc_obj.h

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
// - Graph of GC nodes: everything is an object with an 8 byte header
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
// - NewStr(length), StrFromC(), NewList, NewDict: Alloc() doesn't
// work
//   for these types for various reasons
// - Heap::Allocate()
//   The untyped internal API.  For NewStr() and NewSlab().
// - malloc() -- for say yajl to use.  Manually deallocated.
// - new/delete -- shouldn't be in Oil?

// Slab Sizing with 8-byte slab header
//
//   16 - 8 =  8 = 1 eight-byte or  2 four-byte elements
//   32 - 8 = 24 = 3 eight-byte or  6 four-byte elements
//   64 - 8 = 56 = 7 eight-byte or 14 four-byte elements

// #defines for degbugging:
//
// GC_ALWAYS: Collect() on every Allocate().  Exposes many bugs!
// GC_VERBOSE: Log when we collect

// Silly definition for passing types like GlobalList<T, N> and initializer
// lists like {1, 2, 3} to macros

template <class T>
class List;

struct RawObject;

class Space {
 public:
  Space() {
  }
  void Init(int);

  void Free();

  char* begin_;
  int size_;  // number of bytes
};

class CheneyHeap {
 public:
  CheneyHeap() {  // default constructor does nothing -- relies on zero
                  // initialization
  }

  // Real initialization with the initial heap size.  The heap grows with
  // allocations.
  void Init(int space_size) {
    from_space_.Init(space_size);

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

  void* Allocate(int);

  void Swap() {
    // Swap spaces for next collection.
    char* tmp = from_space_.begin_;
    from_space_.begin_ = to_space_.begin_;
    to_space_.begin_ = tmp;

    int tmp2 = from_space_.size_;
    from_space_.size_ = to_space_.size_;
    to_space_.size_ = tmp2;
  }

  void PushRoot(RawObject** p) {
    // log("PushRoot %d", roots_top_);
    roots_[roots_top_++] = p;
    // TODO: This should be like a malloc() failure?
    assert(roots_top_ < kMaxRoots);
  }

  void PopRoot() {
    roots_top_--;
    // log("PopRoot %d", roots_top_);
  }

  RawObject* Relocate(RawObject* obj, ObjHeader* header);

  // mutates free_ and other variables
  void Collect(int to_space_size = 0);

  // Like MarkSweepHeap
  int MaybeCollect() {
    return -1;
  }

  // Like MarkSweepHeap.  TODO: Does this API work?
  void RootGlobalVar(void* root) {
  }

  // Like MarkSweepHeap
  void CleanProcessExit() {
  }
  void FastProcessExit() {
  }

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
  RawObject** roots_[kMaxRoots];  // These are pointers to RawObject* pointers

  bool is_initialized_ = false;

#if GC_STATS
  int num_collections_;
  int num_heap_growths_;
  int num_forced_growths_;  // when a single allocation is too big
  int num_live_objs_;
#endif
};

#if GC_STATS
void ShowFixedChildren(RawObject* obj);
#endif

#endif  // CHENEY_HEAP_H
