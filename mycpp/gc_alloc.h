// gc_alloc.h: Functions that wrap gHeap.Allocate()

#ifndef MYCPP_GC_ALLOC_H
#define MYCPP_GC_ALLOC_H

#include <string.h>  // strlen

#include <new>      // placement new
#include <utility>  // std::forward

#include "mycpp/gc_obj.h"   // for RawObject, ObjHeader
#include "mycpp/gc_slab.h"  // for NewSlab()
#include "mycpp/gc_str.h"   // for NewStr()

#if defined(BUMP_LEAK)
  #include "mycpp/bump_leak_heap.h"
extern BumpLeakHeap gHeap;
#elif defined(MARK_SWEEP)
  #include "mycpp/mark_sweep_heap.h"
extern MarkSweepHeap gHeap;
#endif

// mycpp generates code that keeps track of the root set
class StackRoot {
 public:
  StackRoot(void* root) {
    RawObject** obj = reinterpret_cast<RawObject**>(root);
    gHeap.PushRoot(obj);
  }

  ~StackRoot() {
    gHeap.PopRoot();
  }
};

// sugar for tests
class StackRoots {
 public:
  // Note: void** seems logical, because these are pointers to pointers, but
  // the C++ compiler doesn't like it.
  StackRoots(std::initializer_list<void*> roots) {
    n_ = roots.size();

#if VALIDATE_ROOTS
    int i = 0;
#endif

    for (auto root : roots) {  // can't use roots[i]
      RawObject** obj = reinterpret_cast<RawObject**>(root);
#if VALIDATE_ROOTS
      ValidateRoot(*obj);
      i++;
#endif

      gHeap.PushRoot(obj);
    }
  }

  ~StackRoots() {
    for (int i = 0; i < n_; ++i) {
      gHeap.PopRoot();
    }
  }

 private:
  int n_;
};

// Note:
// - This function causes code bloat due to template expansion on hundreds of
//   types.  Could switch to a GC_NEW() macro
// - GCC generates slightly larger code if you factor out void* place and new
//   (place) T()
//
// Variadic templates:
// https://eli.thegreenplace.net/2014/variadic-templates-in-c/
template <typename T, typename... Args>
T* Alloc(Args&&... args) {
  // Alloc() allocates space for both a header and object and guarantees that
  // they're adjacent in memory (so that they're at known offsets from one
  // another). However, this means that the address that the object is
  // constructed at is offset from the address returned by the memory allocator
  // (by the size of the header), and therefore may not be sufficiently aligned.
  // Here we assert that the object will be sufficiently aligned by making the
  // equivalent assertion that zero padding would be required to align it.
  // Note: the required padding is given by the following (according to
  // https://en.wikipedia.org/wiki/Data_structure_alignment):
  // `padding = -offset & (align - 1)`.
  static_assert((-sizeof(ObjHeader) & (alignof(T) - 1)) == 0,
                "Expected no padding");

  DCHECK(gHeap.is_initialized_);

  constexpr size_t num_bytes = sizeof(ObjHeader) + sizeof(T);
#if MARK_SWEEP
  int obj_id;
  int pool_id;
  void* place = gHeap.Allocate(num_bytes, &obj_id, &pool_id);
#else
  void* place = gHeap.Allocate(num_bytes);
#endif
  ObjHeader* header = new (place) ObjHeader(T::obj_header());
#if MARK_SWEEP
  header->obj_id = obj_id;
  #ifndef NO_POOL_ALLOC
  header->pool_id = pool_id;
  #endif
#endif
  void* obj = header->ObjectAddress();
  // Now that mycpp generates code to initialize every field, we should
  // get rid of this.
  // TODO: fix uftrace failure, maybe by upgrading, or working around
  memset(obj, 0, sizeof(T));
  return new (obj) T(std::forward<Args>(args)...);
}

//
// String "Constructors".  We need these because of the "flexible array"
// pattern.  I don't think "new BigStr()" can do that, and placement new would
// require mycpp to generate 2 statements everywhere.
//

inline BigStr* NewStr(int len) {
  if (len == 0) {  // e.g. BufLineReader::readline() can use this optimization
    return kEmptyString;
  }

  int obj_len = kStrHeaderSize + len + 1;  // NUL terminator
  const size_t num_bytes = sizeof(ObjHeader) + obj_len;
#if MARK_SWEEP
  int obj_id;
  int pool_id;
  void* place = gHeap.Allocate(num_bytes, &obj_id, &pool_id);
#else
  void* place = gHeap.Allocate(num_bytes);
#endif
  ObjHeader* header = new (place) ObjHeader(BigStr::obj_header());

  auto s = new (header->ObjectAddress()) BigStr();

  s->data_[len] = '\0';  // NUL terminate
  s->len_ = len;
  s->hash_ = 0;
  s->is_hashed_ = 0;

#if MARK_SWEEP
  header->obj_id = obj_id;
  #ifndef NO_POOL_ALLOC
  header->pool_id = pool_id;
  #endif
#endif
  return s;
}

// Call OverAllocatedStr() when you don't know the length of the string up
// front, e.g. with snprintf().  CALLER IS RESPONSIBLE for calling
// s->MaybeShrink() afterward!
inline BigStr* OverAllocatedStr(int len) {
  int obj_len = kStrHeaderSize + len + 1;  // NUL terminator
  const size_t num_bytes = sizeof(ObjHeader) + obj_len;
#if MARK_SWEEP
  int obj_id;
  int pool_id;
  void* place = gHeap.Allocate(num_bytes, &obj_id, &pool_id);
#else
  void* place = gHeap.Allocate(num_bytes);
#endif
  ObjHeader* header = new (place) ObjHeader(BigStr::obj_header());
  auto s = new (header->ObjectAddress()) BigStr();
  s->hash_ = 0;
  s->is_hashed_ = 0;

#if MARK_SWEEP
  header->obj_id = obj_id;
  #ifndef NO_POOL_ALLOC
  header->pool_id = pool_id;
  #endif
#endif
  return s;
}

// Copy C string into the managed heap.
inline BigStr* StrFromC(const char* data, int len) {
  // Optimization that could be taken out once we have SmallStr
  if (len == 0) {
    return kEmptyString;
  }
  BigStr* s = NewStr(len);
  memcpy(s->data_, data, len);
  DCHECK(s->data_[len] == '\0');  // should be true because Heap was zeroed

  return s;
}

inline BigStr* StrFromC(const char* data) {
  return StrFromC(data, strlen(data));
}

// Create a slab with a number of entries of a certain type.
// Note: entries will be zero'd because we use calloc().  TODO: Consider
// zeroing them separately.
template <typename T>
inline Slab<T>* NewSlab(int len) {
  int obj_len = len * sizeof(T);
  const size_t num_bytes = sizeof(ObjHeader) + obj_len;
#if MARK_SWEEP
  int obj_id;
  int pool_id;
  void* place = gHeap.Allocate(num_bytes, &obj_id, &pool_id);
#else
  void* place = gHeap.Allocate(num_bytes);
#endif
  ObjHeader* header = new (place) ObjHeader(Slab<T>::obj_header(len));
  void* obj = header->ObjectAddress();
  if (std::is_pointer<T>()) {
    memset(obj, 0, obj_len);
  }
  auto slab = new (obj) Slab<T>(len);
#if MARK_SWEEP
  header->obj_id = obj_id;
  #ifndef NO_POOL_ALLOC
  header->pool_id = pool_id;
  #endif
#endif
  return slab;
}

#endif  // MYCPP_GC_ALLOC_H
