// gc_alloc.h: Functions that wrap gHeap.Allocate()

#ifndef MYCPP_GC_ALLOC_H
#define MYCPP_GC_ALLOC_H

#include <string.h>  // strlen

#include <new>      // placement new
#include <utility>  // std::forward

#include "mycpp/gc_slab.h"  // for NewSlab()
#include "mycpp/gc_str.h"   // for NewStr()

#if defined(BUMP_LEAK)
  #include "mycpp/bump_leak_heap.h"
extern BumpLeakHeap gHeap;
#elif defined(MARK_SWEEP)
  #include "mycpp/mark_sweep_heap.h"
extern MarkSweepHeap gHeap;
#elif defined(CHENEY_GC)
  #include "mycpp/cheney_heap.h"
extern CheneyHeap gHeap;
#endif

#define VALIDATE_ROOTS 0

// mycpp generates code that keeps track of the root set
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

#if VALIDATE_ROOTS
      RawObject* obj = *(reinterpret_cast<RawObject**>(root));
      if (obj) {
        RawObject* header = FindObjHeader(obj);
        log("obj %p header %p", obj, header);

        switch (header->heap_tag) {
        case HeapTag::Global:
        case HeapTag::Opaque:
        case HeapTag::Scanned:
        case HeapTag::FixedSize:
          break;

        default:
          log("root %d heap %d type %d mask %d len %d", i, header->heap_tag,
              header->type_tag, header->field_mask, header->obj_len);
          FAIL(kShouldNotGetHere);
          break;
        }
      }
      i++;
#endif

      gHeap.PushRoot(reinterpret_cast<RawObject**>(root));
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
  DCHECK(gHeap.is_initialized_);

  void* place = gHeap.Allocate(sizeof(T));
#if MARK_SWEEP
  // IMPORTANT: save the object ID before calling placement new, which can
  // invoke Allocate() again!
  int obj_id = gHeap.UnusedObjectId();
#endif

  T* obj = new (place) T(std::forward<Args>(args)...);

#if MARK_SWEEP
  // Hack for now: find the header
  ObjHeader* header = FindObjHeader(reinterpret_cast<RawObject*>(obj));
  header->obj_id = obj_id;
#endif
  return obj;
}

//
// String "Constructors".  We need these because of the "flexible array"
// pattern.  I don't think "new Str()" can do that, and placement new would
// require mycpp to generate 2 statements everywhere.
//

inline Str* NewStr(int len) {
  if (len == 0) {  // e.g. BufLineReader::readline() can use this optimization
    return kEmptyString;
  }

  int obj_len = kStrHeaderSize + len + 1;

  // only allocation is unconditionally returned
  void* place = gHeap.Allocate(obj_len);

  auto s = new (place) Str();
#if defined(MARK_SWEEP) || defined(BUMP_LEAK)
  STR_LEN(s->header_) = len;
#else
  // reversed in len() to derive string length
  s->header_.obj_len = kStrHeaderSize + len + 1;
#endif

#if MARK_SWEEP
  s->header_.obj_id = gHeap.UnusedObjectId();
#endif
  return s;
}

// Call OverAllocatedStr() when you don't know the length of the string up
// front, e.g. with snprintf().  CALLER IS RESPONSIBLE for calling
// s->MaybeShrink() afterward!
inline Str* OverAllocatedStr(int len) {
  int obj_len = kStrHeaderSize + len + 1;  // NUL terminator
  void* place = gHeap.Allocate(obj_len);
  auto s = new (place) Str();
#if MARK_SWEEP
  s->header_.obj_id = gHeap.UnusedObjectId();
#endif
  return s;
}

// Copy C string into the managed heap.
inline Str* StrFromC(const char* data, int len) {
  // Optimization that could be taken out once we have SmallStr
  if (len == 0) {
    return kEmptyString;
  }
  Str* s = NewStr(len);
  memcpy(s->data_, data, len);
  DCHECK(s->data_[len] == '\0');  // should be true because Heap was zeroed

  return s;
}

inline Str* StrFromC(const char* data) {
  return StrFromC(data, strlen(data));
}

// Create a slab with a number of entries of a certain type.
// Note: entries will be zero'd because we use calloc().  TODO: Consider
// zeroing them separately.
template <typename T>
inline Slab<T>* NewSlab(int len) {
  int obj_len = RoundUp(kSlabHeaderSize + len * sizeof(T));
  void* place = gHeap.Allocate(obj_len);
  auto slab = new (place) Slab<T>(len);  // placement new
#if MARK_SWEEP
  slab->header_.obj_id = gHeap.UnusedObjectId();
#endif
  return slab;
}

#endif  // MYCPP_GC_ALLOC_H
