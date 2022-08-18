// mycpp/gc_heap.h
//
// A garbage collected heap that looks like statically typed Python: Str,
// List<T>, Dict<K, V>.

#ifndef GC_HEAP_H
#define GC_HEAP_H

#include <cassert>  // assert()
#include <cstddef>  // max_align_t
#include <cstdint>  // max_align_t
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
// GC_PROTECT: Use mprotect()
// GC_VERBOSE: Log when we collect
// GC_STATS: Collect more stats.  TODO: Rename this?

// Silly definition for passing types like GlobalList<T, N> and initializer
// lists like {1, 2, 3} to macros

#include "mycpp/gc_tag.h"

template <class T>
class List;

#include "cpp/aligned.h"

class Obj;

const int kMaxRoots = 4 * 1024;  // related to C stack size

class Space {
 public:
  Space() {
  }
  void Init(int space_size);

  void Free();

  void Clear() {
    // Slab scanning relies on 0 bytes (nullptr).  e.g. for a List<Token*>*.
    // Note: I noticed that memset() of say 400 MiB is pretty expensive.  Does
    // it makes sense to zero the slabs instead?
#ifndef NO_GC_HACK
    // When not collecting, we need a huge 400 MiB heap.  Try to save startup
    // time by not doing this.
    memset(begin_, 0, size_);
#endif
  }

#if GC_PROTECT
  // To maintain invariants
  void Protect();
  void Unprotect();
#endif
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
    to_space_.Init(space_size);

    free_ = from_space_.begin_;  // where we allocate from
    limit_ = free_ + space_size;

    roots_top_ = 0;

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

    // It's STILL too small.  Resize to_space_ to ENSURE that allocation will
    // succeed, copy the heap to it, then allocate the object.
    int multiple = 2;
    while (from_space_.size_ + n > to_space_.size_ * multiple) {
      multiple *= 2;
    }
    // log("=== FORCED by multiple of %d", multiple);
    to_space_.Free();
    to_space_.Init(to_space_.size_ * multiple);

    Collect();
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
  void Collect();

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

template <typename T>
class Local {
  // We can garbage collect at any Alloc() invocation, so we need a level of
  // indirection for locals / pointers directly on the stack.  Pointers on the
  // heap are updated by the Cheney GC algorithm.

 public:
  Local() : raw_pointer_(nullptr) {
  }

  // IMPLICIT conversion.  No 'explicit'.
  Local(T* raw_pointer) : raw_pointer_(raw_pointer) {
    // TODO(Jesse): Does this get called?
    // Is this NotImplemented() or InvalidCodePath() ??
    assert(0);
    // gHeap.PushRoot(this);
  }

  // Copy constructor, e.g. f(mylocal) where f(Local<T> param);
  Local(const Local& other) : raw_pointer_(other.raw_pointer_) {
    // TODO(Jesse): Does this get called?
    // Is this NotImplemented() or InvalidCodePath() ??
    assert(0);
    // gHeap.PushRoot(this);
  }

  void operator=(const Local& other) {  // Assignment operator
    raw_pointer_ = other.raw_pointer_;

    // Note: we could try to avoid PushRoot() as an optimization.  Example:
    //
    // Local<Str> a = StrFromC("foo");
    // Local<Str> b;
    // b = a;  // invokes operator=, it's already a root
    //
    // Local<Str> c = myfunc();  // T* constructor takes care of PushRoot()

    // log("operator=");

    // However the problem is that then we'll have an unbalanced PopRoot().
    // So we keep it for now.
    gHeap.PushRoot(this);
  }

  ~Local() {
    gHeap.PopRoot();
  }

  // This cast operator overload allows:
  //
  // Local<Str> s = StrFromC("foo");
  // node->mystr = s;  // convert from Local to raw
  //
  // As well as:
  //
  // Local<List<Str*>> strings = Alloc<List<Str*>>();
  // strings->append(StrFromC("foo"));  // convert from local to raw
  //
  // The heap should NOT have locals!  List<Str> and not List<Local<Str>>.
  //
  // Note: This could be considered dangerous if we don't maintain
  // discipline.
  //
  // https://www.informit.com/articles/article.aspx?p=31529&seqNum=7
  //
  // Putting .get() at the call site in mycpp is more explicit. The
  // readability of the generated code is important!
#if 1
  operator T*() {
    return raw_pointer_;
  }
#endif

  // Allows ref->field and ref->method()
  T* operator->() const {
    // log("operator->");
    return raw_pointer_;
  }
  T* Get() const {
    return raw_pointer_;
  }
  // called by the garbage collector when moved to a new location!
  void Update(T* moved) {
    raw_pointer_ = moved;
  }

  // Dereference to get the real value.  Doesn't seem like we need this.
#if 0
  T operator*() const {
    //log("operator*");
    return *raw_pointer_;
  }
#endif

  T* raw_pointer_;
};

template <typename T>
class Param : public Local<T> {
  // This could be an optimization like SpiderMonkey's Handle<T> vs Rooted<T>.
  // We use the names Param<T> and Local<T>.

 public:
  // hm this is awkward, I think we should NOT inherit!  We should only
  // convert.
  Param(const Local<T>& other) : Local<T>(nullptr) {
    this->raw_pointer_ = other.raw_pointer_;
  }

  ~Param() {  // do not PopRoot()
  }

  // Construct from T* -- PushRoot()
  // Construct from Local<T> -- we don't need to PushRoot()
  // operator= -- I don't think we need to PushRoot()
};

#include "mycpp/gc_alloc.h"
#include "mycpp/gc_obj.h"

#endif  // GC_HEAP_H
