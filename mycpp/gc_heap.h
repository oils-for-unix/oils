#ifndef GC_HEAP_H
#define GC_HEAP_H

#include "cheney_heap.h"
#include "marksweep_heap.h"

#if MARK_SWEEP
  #define PRINT_GC_MODE_STRING() printf("  -- GC_MODE :: marksweep\n")
extern MarkSweepHeap gHeap;
#else
  #define PRINT_GC_MODE_STRING() printf("  -- GC_MODE :: cheney\n")
extern CheneyHeap gHeap;
#endif

class RootingScope {
  // Create an instance of this in every function.  This lets the GC now when
  // functions return, so it can remove values from the root set.

 public:
  RootingScope() {
    gHeap.root_set_.PushScope();
  }
  ~RootingScope() {
    gHeap.root_set_.PopScope();
  }
};

// Variadic templates:
// https://eli.thegreenplace.net/2014/variadic-templates-in-c/
template <typename T, typename... Args>
T* Alloc(Args&&... args) {
  // RootingScope omitted for PASS THROUGH

  assert(gHeap.is_initialized_);
  void* place = gHeap.Allocate(sizeof(T));
  assert(place != nullptr);
  // placement new
  return new (place) T(std::forward<Args>(args)...);
}

class StackRoots {
 public:
  StackRoots(std::initializer_list<void*> roots) {
    n_ = roots.size();
    for (auto root : roots) {  // can't use roots[i]
      gHeap.PushRoot(reinterpret_cast<Obj**>(root));
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

// for Tag::FixedSize
class LayoutFixed : public Obj {
 public:
  Obj* children_[16];  // only the entries denoted in field_mask will be valid
};

#endif  // GC_HEAP_H
