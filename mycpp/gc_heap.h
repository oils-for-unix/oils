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
// - gc_heap::Alloc<Foo>(x)
//   The typed public API.  An alternative to new Foo(x).  mycpp/ASDL should
//   generate these calls.
// - AllocStr(length), StrFromC(), NewList, NewDict: gc_heap::Alloc() doesn't
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

// Obj::heap_tag_ values.  They're odd numbers to distinguish them from vtable
// pointers.
namespace Tag {
const int Forwarded = 1;  // For the Cheney algorithm.
const int Global = 3;     // Neither copy nor scan.
const int Opaque = 5;     // Copy but don't scan.  List<int> and Str
const int FixedSize = 7;  // Fixed size headers: consult field_mask_
const int Scanned = 9;    // Copy AND scan for non-NULL pointers.
}  // namespace Tag

// Silly definition for passing types like GlobalList<T, N> and initializer
// lists like {1, 2, 3} to macros

#define COMMA ,

namespace gc_heap {

template <class T>
class List;

constexpr int kMask = alignof(max_align_t) - 1;  // e.g. 15 or 7

// Align returned pointers to the worst case of 8 bytes (64-bit pointers)
inline size_t aligned(size_t n) {
  // https://stackoverflow.com/questions/2022179/c-quick-calculation-of-next-multiple-of-4
  // return (n + 7) & ~7;

  return (n + kMask) & ~kMask;
}

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

// Variadic templates:
// https://eli.thegreenplace.net/2014/variadic-templates-in-c/
template <typename T, typename... Args>
T* Alloc(Args&&... args) {
  void* place = gHeap.Allocate(sizeof(T));
  assert(place != nullptr);
  // placement new
  return new (place) T(std::forward<Args>(args)...);
}

// Return the size of a resizeable allocation.  For now we just round up by
// powers of 2. This could be optimized later.  CPython has an interesting
// policy in listobject.c.
//
// https://stackoverflow.com/questions/466204/rounding-up-to-next-power-of-2
inline int RoundUp(int n) {
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

}  // namespace gc_heap

#endif  // GC_HEAP_H
