// gc_heap.h
//
// A garbage collected heap that looks like statically typed Python: Str,
// List, Dict.

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

#include "common.h"

// Design Notes:

// We're starting off very simple: It's a semi-space collector using the Cheney
// algorithm.  (Later we may add a "large object space", managed by
// mark-and-sweep after each copy step.)

// Design:
// - Immutable Slab<T> and Str (Str may have a hash value and other fields).
// - Mutable List and Dict that point to Slab
//   - List::append() and extend() can realloc
//   - Dict::set() can realloc and rehash

// TODO:
// - Dicts should actually use hashing!  Test computational complexity.

// Memory allocation APIs:
//
// - gc_heap::Alloc<Foo>(x)
//   The typed public API.  An alternative to new Foo(x).  mycpp/ASDL should
//   generate these calls.
// - Heap::Allocate()
//   The untyped internal API.  For NewStr() and NewSlab().
// - malloc() -- for say yajl to use.  Manually deallocated.
// - new/delete -- for other C++ libs to use.  Manually deallocated.

// Must use Local<T> instead of raw pointers on the stack.
//
//   This implements "double indirection".
//
//   Why do we need signatures like len(Local<Str> s) and len(Local<List<T>> L)
//   ?  Consider a call like len(["foo"]).  If len() allocated, we could lose
//   track of ["foo"], if it weren't registered with PushRoot().
//
//   Example:
//
//   Str* myfunc(Local<Str> s) {  /* takes Local, returns raw pointer */
//     // allocation may trigger collection
//     Local<Str> suffix = NewStr("foo");
//     return str_concat(s, suffix);
//   }
//   // Pointer gets coerced to Local?  But not the reverse.
//   Local<Str> result = myfunc(NewStr("bar"));
//
//   TODO: godbolt an example with Local<T>, to see how much it costs.  I hope
//   it could be optimized away.
//
//   https://developer.mozilla.org/en-US/docs/Mozilla/Projects/SpiderMonkey/GC_Rooting_Guide
//   Our Local<T> is like their Rooted<T>
//
//   "JS::Handle<T> exists because creating and destroying a JS::Rooted<T> is
//   not free (though it only costs a few cycles). Thus, it makes more sense to
//   only root the GC thing once and reuse it through an indirect reference.
//   Like a reference, a JS::Handle is immutable: it can only ever refer to the
//   JS::Rooted<T> that it was created for."
//   "Return raw pointers from functions"
//
//   Hm I guess we could have two types.  But do the dumb thing for now.
//
//   They have MutableHandle<T> for out params, but we don't have out params!

// Slab Sizing with 8-byte slab header
//
//   16 - 8 =  8 = 1 eight-byte or  2 four-byte elements
//   32 - 8 = 24 = 3 eight-byte or  6 four-byte elements
//   64 - 8 = 56 = 7 eight-byte or 14 four-byte elements
//
// Note: dict will have DIFFERENT size keys and values!  It has its own
// calculation.

// Small Size Optimization: omit separate slabs (later)
//
// - List: 24 bytes, so we could get 1 or 2 entries for free?  That might add
//   up
// - Dict: 40 bytes: I don't think it optimizes
// - Doesn't apply to Str because it's immutable: 16 bytes + string length.

// TODO: Reconcile these with ASDL tags.  Those are all FixedSize, so I guess
// that should be a high bit?  0xC000  3 && Tag::FixedSize
namespace Tag {
const int Forwarded = 1;  // For the Cheney algorithm.
const int Global = 2;     // Neither copy nor scan.
const int Opaque = 3;     // Copy but don't scan.  List<int> and Str
const int FixedSize = 4;  // Fixed size headers: consult field_mask_
const int Scanned = 5;    // Copy AND scan for non-NULL pointers.
}  // namespace Tag

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

const int kMaxRoots = 1024;  // related to C stack size

// #define GC_DEBUG 1

class Heap {
 public:
  Heap() {  // default constructor does nothing -- relies on zero initialization
  }

  // Real initialization with the initial heap size.  The heap grows with
  // allocations.
  void Init(int num_bytes) {
    from_space_ = static_cast<char*>(malloc(num_bytes));
    to_space_ = static_cast<char*>(malloc(num_bytes));
    limit_ = from_space_ + num_bytes;

    free_ = from_space_;  // where we allocate from
    scan_ = nullptr;

    space_size_ = num_bytes;
    grew_ = false;

    roots_top_ = 0;

    // Slab scanning relies on 0 bytes (nullptr).  e.g. for a List<Token*>*.
    // Note: I noticed that memset() of say 400 MiB is pretty expensive.  Does
    // it makes sense to zero the slabs instead?
    memset(from_space_, 0, num_bytes);
    memset(to_space_, 0, num_bytes);

#if GC_DEBUG
    num_live_objs_ = 0;
#endif
  }

  void* Allocate(int num_bytes) {
    char* p = free_;
    int n = aligned(num_bytes);
    // log("n = %d, p = %p", n, p);
    //

    // Possible: optimization: do it if we have less than 20% free space.
    // bool almost_full = (limit_ - free_) < (space_size_ / 5);
    // This is still a correct GC algorithm
    bool almost_full = false;

    // Do a collection if REQUIRED.
    if (almost_full || free_ + n > limit_) {
#if GC_DEBUG
      log("GC free_ %p,  from_space_ %p, space_size_ %d", free_, from_space_,
          space_size_);
#endif

      Collect(false);
      // Three cases at the end of Collect:
      // - We have more than 20% free space, and we didn't grow.
      // - We have less than 20% free space, but more than zero, and we grew.
      //   A future collection will grow (or it may never happen).
      // - NOTHING was collected.  We have zero space, and we need to collect
      //   NOW with must_grow=true.  This is unlikely.

      while (free_ + n > limit_) {
        Collect(true);
      }

      // Allocate again, using new free_ pointer
      return Allocate(num_bytes);
    }

    free_ += n;

#if GC_DEBUG
    num_live_objs_++;
#endif

    return p;
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

  Obj* Relocate(Obj* obj);

  // mutates free_ and other variables
  void Collect(bool must_grow);

  char* from_space_;  // beginning of the space we're allocating from
  char* to_space_;    // beginning of the space we should copy to
  char* limit_;       // end of space we're allocating from

  char* scan_;  // boundary between black and grey
  char* free_;  // next place to allocate, from_space_ <= free_ < limit_

  int space_size_;  // current size of space.  NOT redundant with limit_ because
                    // of resizing
  bool grew_;       // did the TO SPACE grow on the last collection?

  // Stack roots.  The obvious data structure is a linked list, but an array
  // has better locality.
  //
  // femtolisp uses a global pointer to dynamically-allocated growable array,
  // with initial N_STACK = 262144!  Kind of arbitrary.

  int roots_top_;
  Obj** roots_[kMaxRoots];  // These are pointers to Obj* pointers

#if GC_DEBUG
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
    assert(0);
    // gHeap.PushRoot(this);
  }

  // Copy constructor, e.g. f(mylocal) where f(Local<T> param);
  Local(const Local& other) : raw_pointer_(other.raw_pointer_) {
    assert(0);
    // gHeap.PushRoot(this);
  }

  void operator=(const Local& other) {  // Assignment operator
    raw_pointer_ = other.raw_pointer_;

    // Note: we could try to avoid PushRoot() as an optimization.  Example:
    //
    // Local<Str> a = NewStr("foo");
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
    // Local<Str> s = NewStr("foo");
    // node->mystr = s;  // convert from Local to raw
    //
    // As well as:
    //
    // Local<List<Str*>> strings = Alloc<List<Str*>>();
    // strings->append(NewStr("foo"));  // convert from local to raw
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

  void SetCellLength(int obj_len) {
    this->obj_len_ = obj_len;
  }

  OBJ_HEADER()

  DISALLOW_COPY_AND_ASSIGN(Obj)
};

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

// Opaque slab.  e.g. for String data
template <typename T>
class Slab : public Obj {
 public:
  Slab(int obj_len) : Obj(0, 0, obj_len) {
    InitSlabCell<T>(this);
  }
  T items_[1];  // variable length
};

// Note: entries will be zero'd because the Heap is zero'd.
template <typename T>
inline Slab<T>* NewSlab(int len) {
  int obj_len = RoundUp(kSlabHeaderSize + len * sizeof(T));
  void* place = gHeap.Allocate(obj_len);
  auto slab = new (place) Slab<T>(obj_len);  // placement new
  return slab;
}

#ifdef MYLIB_LEGACY
#define GLOBAL_STR(name, val) Str* name = new Str(val);
#endif

#ifndef MYLIB_LEGACY

//
// Str
//

class Str : public gc_heap::Obj {
 public:
  // Don't call this directly.  Call NewStr() instead, which calls this.
  explicit Str() : Obj(Tag::Opaque, kZeroMask, 0) {
    // log("GC Str()");
  }

  Str* index(int i);
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
    assert(0);
  }

  Str* lower() {
    assert(0);
  }

  int unique_id_;  // index into intern table ?
  char data_[1];   // flexible array

 private:
  int _strip_left_pos();
  int _strip_right_pos();

  DISALLOW_COPY_AND_ASSIGN(Str)
};

template <int N>
class GlobalStr {
  // A template type with the same layout as Str with length N-1 (which needs a
  // buffer of size N).  For initializing global constant instances.
 public:
  OBJ_HEADER()

  int unique_id_;
  const char data_[N];

  DISALLOW_COPY_AND_ASSIGN(GlobalStr)
};

// This is the same as offsetof(Str, data_), but doesn't give a warning,
// because of the inheritance?
constexpr int kStrHeaderSize = offsetof(GlobalStr<1>, data_);

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

// Note: sizeof("foo") == 4, for the NUL terminator.

// Hm we're getting a warning because these aren't plain old data?
// https://stackoverflow.com/questions/1129894/why-cant-you-use-offsetof-on-non-pod-structures-in-c
// https://stackoverflow.com/questions/53850100/warning-offset-of-on-non-standard-layout-type-derivedclass

// The structures must be layout compatible!  Protect against typos.
static_assert(offsetof(Str, data_) == offsetof(GlobalStr<1>, data_), "oops");

//
// String "Constructors".  We need these because of the "flexible array"
// pattern.  I don't think "new Str()" can do that, and placement new would
// require mycpp to generate 2 statements everywhere.
//

// New string of a certain length, to be filled in
inline Str* NewStr(int len) {
  int obj_len = kStrHeaderSize + len + 1;  // NUL terminator
  void* place = gHeap.Allocate(obj_len);   // immutable, so allocate exactly
  auto s = new (place) Str();
  s->SetCellLength(obj_len);  // So the GC can copy it
  return s;
}

inline Str* NewStr(const char* data, int len) {
  Str* s = NewStr(len);

  // log("NewStr s->data_ %p len = %d", s->data_, len);
  // log("sizeof(Str) = %d", sizeof(Str));
  memcpy(s->data_, data, len);
  assert(s->data_[len] == '\0');  // should be true because Heap was zeroed

  return s;
}

// CHOPPED OFF at internal NUL.  Use explicit length if you have a NUL.
inline Str* NewStr(const char* data) {
  return NewStr(data, strlen(data));
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

//
// List<T>
//

// Type that is layout-compatible with List to avoid invalid-offsetof warnings.
// Unit tests assert that they have the same layout.
class _DummyList {
 public:
  OBJ_HEADER()
  int len_;
  int capacity_;
  void* slab_;
};

// A list has one Slab pointer which we need to follow.
constexpr uint16_t maskof_List() {
  return maskbit(offsetof(_DummyList, slab_));
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
  List()
      : Obj(Tag::FixedSize, maskof_List(), sizeof(List<T>)),
        len_(0),
        capacity_(0),
        slab_(nullptr) {
  }

  // Literal ['foo', 'bar']
  List(std::initializer_list<T> init)
      : Obj(Tag::FixedSize, maskof_List(), sizeof(List<T>)), slab_(nullptr) {
    int n = init.size();
    reserve(n);

    int i = 0;
    for (auto item : init) {
      set(i, item);
      ++i;
    }
    len_ = n;
  }

  // list_repeat ['foo'] * 3
  List(T item, int times)
      : Obj(Tag::FixedSize, maskof_List(), sizeof(List<T>)),
        len_(0),  // can't set this before reserve()
        capacity_(0),
        slab_(nullptr) {
    reserve(times);
    len_ = times;
    for (int i = 0; i < times; ++i) {
      set(i, item);
    }
  }

  // Internal constructor for keys() and values()
  List(Slab<T>* from_slab, int n)
      : Obj(Tag::FixedSize, maskof_List(), sizeof(List<T>)),
        len_(0),  // can't set this before reserve()
        capacity_(0),
        slab_(nullptr) {
    reserve(n);
    len_ = n;
    memcpy(slab_->items_, from_slab->items_, n * sizeof(T));
  }

  // Implements L[i]
  T index(int i) {
    if (i < len_) {
      return slab_->items_[i];
    } else {
      log("i = %d, len_ = %d", i, len_);
      assert(0);  // Out of bounds
    }
  }

  // Implements L[i] = item
  void set(int i, T item) {
    slab_->items_[i] = item;
  }

  // L[begin:]
  List* slice(int begin) {
    if (begin == 0) {
      return this;
    }
    if (begin < 0) {
      begin = len_ + begin;
    }

    List* result = Alloc<List<T>>();  // TODO: initialize with size
    for (int i = begin; i < len_; i++) {
      result->append(slab_->items_[i]);
    }
    return result;
  }

  // L[begin:end]
  // TODO: Can this be optimized?
  List* slice(int begin, int end) {
    if (begin < 0) {
      begin = len_ + begin;
    }
    if (end < 0) {
      end = len_ + end;
    }

    List* result = new List();  // TODO: initialize with size
    for (int i = begin; i < end; i++) {
      result->append(slab_->items_[i]);
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
    T result = index(0);

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
  void sort() {
    mysort(slab_->items_, slab_->items_ + len_);
  }

  // 8 / 4 = 2 items, or 8 / 8 = 1 item
  static const int kCapacityAdjust = kSlabHeaderSize / sizeof(T);
  static_assert(kSlabHeaderSize % sizeof(T) == 0,
                "Slab header size should be multiple of item size");

  // Ensure that there's space for a number of items
  void reserve(int n) {
    // log("reserve capacity = %d, n = %d", capacity_, n);

    if (capacity_ < n) {
      // Example: The user asks for space for 7 integers.  Account for the
      // header, and say we need 9 to determine the obj length.  9 is
      // rounded up to 16, for a 64-byte obj.  Then we actually have space
      // for 14 items.
      capacity_ = RoundUp(n + kCapacityAdjust) - kCapacityAdjust;
      auto new_slab = NewSlab<T>(capacity_);

      // slab_ may not be initialized constructor because many lists are
      // empty.
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

  // Extend this list with multiple elements.
  void extend(List<T>* other) {
    int n = other->len_;
    int new_len = len_ + n;
    reserve(new_len);

    for (int i = 0; i < n; ++i) {
      set(len_ + i, other->slab_->items_[i]);
    }
    len_ = new_len;
  }

  int len_;       // number of entries
  int capacity_;  // max entries before resizing

  // The container may be resized, so this field isn't in-line.
  Slab<T>* slab_;

  DISALLOW_COPY_AND_ASSIGN(List)
};

//
// Dict<K, V>
//

// Non-negative entries in index_ are array indices into keys_ and values_.
// There are two special negative entries.

// index that means this Dict item was deleted (a tombstone).
const int kDeletedEntry = -1;

// index that means this Dict entry is free.  Because we have Dict[int, int],
// we can't use a sentinel entry in keys_.  It has to be a sentinel entry in
// index_.
const int kEmptyEntry = -2;

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
  void* index_;
  void* keys_;
  void* values_;
};

// A list has one Slab pointer which we need to follow.
constexpr uint16_t maskof_Dict() {
  return maskbit(offsetof(_DummyDict, index_)) |
         maskbit(offsetof(_DummyDict, keys_)) |
         maskbit(offsetof(_DummyDict, values_));
}

template <class K, class V>
class Dict : public gc_heap::Obj {
 public:
  Dict()
      : gc_heap::Obj(Tag::FixedSize, maskof_Dict(), 0),
        len_(0),
        capacity_(0),
        index_(nullptr),
        keys_(nullptr),
        values_(nullptr) {
  }

  // This relies on the fact that containers of 4-byte ints are reduced by 2
  // items, which is greater than (or equal to) the reduction of any other
  // type
  static const int kCapacityAdjust = kSlabHeaderSize / sizeof(int);
  static_assert(kSlabHeaderSize % sizeof(int) == 0,
                "Slab header size should be multiple of key size");

  void reserve(int n) {
    // log("--- reserve %d", capacity_);
    //
    if (capacity_ < n) {  // TODO: use load factor, not exact fit
      // calculate the number of keys and values we should have
      capacity_ = RoundUp(n + kCapacityAdjust) - kCapacityAdjust;

      // TODO: This is SPARSE.  How to compute a size that ensures a decent
      // load factor?
      int index_len = capacity_;
      auto new_i = NewSlab<int>(index_len);

      // For the linear search to work
      for (int i = 0; i < index_len; ++i) {
        new_i->items_[i] = kEmptyEntry;
      }

      // These are DENSE.
      auto new_k = NewSlab<K>(capacity_);
      auto new_v = NewSlab<V>(capacity_);

      if (keys_ != nullptr) {
        // Copy the old index.  Note: remaining entries should be zero'd
        // because of Allocate() behavior.
        memcpy(new_i->items_, index_->items_, index_->obj_len_);

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
    int pos = key_to_pos(key);
    if (pos == -1) {
      assert(0);
    } else {
      return values_->items_[pos];
    }
  }

  // Get a key.
  // Returns nullptr if not found (Can't use this for non-pointer types?)
  V get(K key) {
    int pos = key_to_pos(key);
    if (pos == -1) {
      return nullptr;
    } else {
      return values_->items_[pos];
    }
  }

  // Get a key, but return a default if not found.
  // expr_parse.py uses this with OTHER_BALANCE
  V get(K key, V default_val) {
    int pos = key_to_pos(key);
    if (pos == -1) {
      return default_val;
    } else {
      return values_->items_[pos];
    }
  }

  // Implements d[k] = v.  May resize the dictionary.
  void set(K key, V val) {
    int pos = key_to_pos(key);
    if (pos == -1) {  // new pair
      reserve(len_ + 1);
      keys_->items_[len_] = key;
      values_->items_[len_] = val;

      index_->items_[len_] = 0;  // new special value

      ++len_;
    } else {
      values_->items_[pos] = val;
    }
  }

  // TODO: Remove deleted items!
  List<K>* keys() {
    // Make a copy of the Slab
    return Alloc<List<K>>(keys_, len_);
  }

  // For AssocArray transformations
  List<V>* values() {
    return Alloc<List<V>>(values_, len_);
  }

  void clear() {
    // Maintain invariant
    for (int i = 0; i < capacity_; ++i) {
      index_->items_[i] = kEmptyEntry;
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
  int key_to_pos(K key) {
    for (int i = 0; i < capacity_; ++i) {
      int special = index_->items_[i];  // NOT an index now
      if (special == kDeletedEntry) {
        continue;  // keep searching
      }
      if (special == kEmptyEntry) {
        return -1;  // not found
      }
      if (keys_equal(keys_->items_[i], key)) {
        return i;
      }
    }
    return -1;  // table is completely full?  Does this happen?
  }

  // int index_size_;  // size of index (sparse)
  int len_;       // number of entries (keys and values, almost dense)
  int capacity_;  // number of entries before resizing

  // These 3 slabs are resized at the same time.
  Slab<int>* index_;  // NOW: kEmptyEntry, kDeletedEntry, or 0.
                      // LATER: indices which are themselves indexed by // hash
                      // value % capacity_
  Slab<K>* keys_;     // Dict<int, V>
  Slab<V>* values_;   // Dict<K, int>

  DISALLOW_COPY_AND_ASSIGN(Dict)
};

#if GC_DEBUG
void ShowFixedChildren(Obj* obj);
#endif

#endif  // MYLIB_LEGACY

}  // namespace gc_heap

//
// Functions
//

#ifndef MYLIB_LEGACY

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

#endif  // MYLIB_LEGACY

#endif  // GC_HEAP_H
