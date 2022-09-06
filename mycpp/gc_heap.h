
#ifdef MARK_SWEEP
  #include "marksweep_heap.h"
#else
  #include "cheney_heap.h"
#endif

extern Heap gHeap;

// Variadic templates:
// https://eli.thegreenplace.net/2014/variadic-templates-in-c/
template <typename T, typename... Args>
T* Alloc(Args&&... args) {
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
    // TODO: optimize this
    for (int i = 0; i < n_; ++i) {
      gHeap.PopRoot();
    }
  }

 private:
  int n_;
};
