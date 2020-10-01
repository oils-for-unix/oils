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
// - Allocate() should Collect() -- hook up that policy.
// - Resize the heap!  This only happens when there's a really large
//   allocation?  More than 20% of the heap.
// - How can we make the field masks portable?
//   - Do we need some kind of constexpr computation?  sizeof(int) vs
//   sizeof(void*)
// - Dicts should actually use hashing!  Test computational complexity.
// - Don't collect or copy GLOBAL Str* instances
//   - Do they have a special tag in the Obj header?
//   - can they be constexpr in the generated source?  Would be nice.

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

constexpr int kMask = alignof(max_align_t) - 1;  // e.g. 15 or 7

// Align returned pointers to the worst case of 8 bytes (64-bit pointers)
inline size_t aligned(size_t n) {
  // https://stackoverflow.com/questions/2022179/c-quick-calculation-of-next-multiple-of-4
  // return (n + 7) & ~7;

  return (n + kMask) & ~kMask;
}

class Obj;

const int kMaxRoots = 1024;  // related to C stack size

#define GC_DEBUG 1

class Heap {
 public:
  Heap() {  // default constructor does nothing -- relies on zero initialization
  }

  // Real initialization with the initial heap size.  The heap grows with
  // allocations.
  void Init(int num_bytes) {
    from_space_ = static_cast<char*>(malloc(num_bytes));
    to_space_ = static_cast<char*>(malloc(num_bytes));

    free_ = from_space_;  // where we allocate from
    scan_ = nullptr;

    // slab scanning relies on 0 bytes (nullptr)
    memset(from_space_, 0, num_bytes);
    memset(to_space_, 0, num_bytes);

    space_size_ = num_bytes;

    roots_top_ = 0;

#if GC_DEBUG
    num_live_objs_ = 0;
#endif
  }

  void* Allocate(int num_bytes) {
    char* p = free_;
    free_ += aligned(num_bytes);

    // TODO: realloc it here
    if (free_ >= from_space_ + space_size_) {
      log("free_ %p  from_space_ %p  space_size_ %d", free_, from_space_,
          space_size_);
      assert(0);
    }

#if GC_DEBUG
    num_live_objs_++;
#endif

    return p;
  }

  void PushRoot(void* p) {
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
  void Collect();

  char* from_space_;
  char* to_space_;

  char* scan_;  // boundary between black and grey
  char* free_;  // next place to

  int space_size_;  // current size

  bool grew_;  // did we grow the last time?

  // Stack roots.  The obvious data structure is a linked list, but an array
  // has better locality.
  //
  // femtolisp uses a global pointer to dynamically-allocated growable array,
  // with initial N_STACK = 262144!  Kind of arbitrary.

  int roots_top_;
  void* roots_[kMaxRoots];  // TODO: Could be Handle<void*> ?

#if GC_DEBUG
  int num_live_objs_;
#endif

  // TODO:
  //   reallocation policy?
};

// The heap is a (compound) global variable.  Notes:
// - The default constructor does nothing, to avoid initialization order
//   problems.
// - For some applications, this can be thread_local rather than global.
extern Heap gHeap;

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
    gHeap.PushRoot(this);
  }

  // Copy constructor, e.g. f(mylocal) where f(Local<T> param);
  Local(const Local& other) : raw_pointer_(other.raw_pointer_) {
    gHeap.PushRoot(this);
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
// tag_: ASDL tag (variant)
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
  T items_[1];  // minimum string obj_len_
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
  }

  int unique_id_;  // index into intern table ?
  char data_[1];   // flexible array

  DISALLOW_COPY_AND_ASSIGN(Str)
};

constexpr int kStrHeaderSize = offsetof(Str, data_);

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

// The structures must be layout compatible!  Protect against typos.
static_assert(offsetof(Str, data_) == offsetof(GlobalStr<1>, data_), "oops");

//
// String "Constructors".  We need these because of the "flexible array"
// pattern.  I don't think "new Str()" can do that, and placement new would
// require mycpp to generate 2 statements everywhere.
//

inline Str* NewStr(const char* data, int len) {
  int obj_len = kStrHeaderSize + len + 1;  // NUL terminator
  void* place = gHeap.Allocate(obj_len);   // immutable, so allocate exactly
  auto s = new (place) Str();

  memcpy(s->data_, data, len);
  s->data_[len] = '\0';  // So we can pass it directly to C functions

  s->SetCellLength(obj_len);  // So the GC can copy it
  return s;
}

inline Str* NewStr(const char* data) {
  return NewStr(data, strlen(data));
}

//
// List<T>
//

// This is one slab in the second position.  TODO: This is different for 32
// bit???  Is there a way to make it portable?
const int kListMask = 0x0002;  // in binary: 0b 0000 0000 0000 00010

template <typename T>
class List : public gc_heap::Obj {
 public:
  List()
      : gc_heap::Obj(Tag::FixedSize, kListMask, sizeof(List<T>)),
        len_(0),
        capacity_(0),
        slab_(nullptr) {
  }

    // TODO: are we using this?
#if 0
  List(std::initializer_list<T> init)
      : Obj(Tag::FixedSize, kListMask, sizeof(List<T>)), slab_(nullptr) {
    extend(init);
  }
#endif

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
    log("reserve capacity = %d, n = %d", capacity_, n);

    if (capacity_ < n) {
      // Example: The user asks for space for 7 integers.  Account for the
      // header, and say we need 9 to determine the obj length.  9 is rounded
      // up to 16, for a 64-byte obj.  Then we actually have space for 14
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

  DISALLOW_COPY_AND_ASSIGN(List)
};

//
// Dict<K, V>
//

template <typename K>
int find_by_key(Slab<K>* keys_, int len, int key) {
  for (int i = 0; i < len; ++i) {
    if (keys_->items_[i] == key) {
      return i;
    }
  }
  return -1;
}

bool str_equals(Str* left, Str* right);

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
class Dict : public gc_heap::Obj {
 public:
  Dict()
      : gc_heap::Obj(Tag::FixedSize, kDictMask, 0),
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

// TODO: Move to mylib?
using gc_heap::Dict;
using gc_heap::List;
using gc_heap::Local;
using gc_heap::Str;

// For string methods to use, e.g. _len(this).  Note: it might be OK to call
// this len() and overload it?
inline int _len(const Str* s) {
  return s->obj_len_ - gc_heap::kStrHeaderSize - 1;
}

// Hm only functions that don't allocate can take a raw pointer ...
// If they allocate, then that pointer can be moved out from under them!

// Hm do all standard library functions have to take Handles now?
inline int len(Local<Str> s) {
  return _len(s.Get());
}

template <typename T>
int len(const List<T>* L) {
  return L->len_;
}

template <typename K, typename V>
inline int len(const Dict<K, V>* d) {
  return d->len_;
}

#endif  // MYLIB_LEGACY

#endif  // GC_HEAP_H
