// gc_alloc.h: Functions that wrap gHeap

#ifndef MYCPP_GC_ALLOC_H
#define MYCPP_GC_ALLOC_H

#include <new>      // placement new
#include <utility>  // std::forward

#define VALIDATE_ROOTS 0

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

          assert(0);
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

  // TODO: get object ID, FindObjHeader(), and set it after construciton
  return new (gHeap.Allocate(sizeof(T))) T(std::forward<Args>(args)...);
}

#endif  // MYCPP_GC_ALLOC_H
