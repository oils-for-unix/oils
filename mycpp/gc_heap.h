#ifndef GC_HEAP_H
#define GC_HEAP_H

#include "mycpp/bump_leak_heap.h"
#include "mycpp/marksweep_heap.h"

#if defined(MARK_SWEEP)
  #define PRINT_GC_MODE_STRING() printf("  -- GC_MODE :: marksweep\n")
#elif defined(BUMP_LEAK)
  #define PRINT_GC_MODE_STRING() printf("  -- GC_MODE :: bumpleak\n")
#else
  #define PRINT_GC_MODE_STRING() printf("  -- GC_MODE :: cheney\n")
#endif

class RootsFrame {
  // Create an instance of this in every function.  This lets the GC now when
  // functions return, so it can remove values from the root set.
  //
  // Example:
  //
  //   RootsFrame _r{FUNC_NAME};
  //   RootsFrame _r{LOOP};
  //
  // You must use braced initialization!
  //
  //   RootsFrame _r(FUNC_NAME);  // WRONG because it sometimes expands to:
  //   RootsFrame _r();           // MOST VEXING PARSE: a function prototype,
  //                              // not a variable

 public:
#ifdef COLLECT_COVERAGE
  explicit RootsFrame(const char* description) {
    log(">>> %s", description);
  #ifndef BUMP_LEAK
    gHeap.root_set_.PushFrame();
  #endif
  }
#endif

  RootsFrame() {
#ifndef BUMP_LEAK
    gHeap.root_set_.PushFrame();
#endif
  }
  ~RootsFrame() {
#ifndef BUMP_LEAK
    gHeap.root_set_.PopFrame();
#endif
  }
};

// Explicit annotation for "skipped frame" optimization, and the like

#define NO_ROOTS_FRAME(description)

#ifdef COLLECT_COVERAGE
  #define FUNC_NAME __PRETTY_FUNCTION__
  // TODO: create a different string for loops
  #define LOOP __PRETTY_FUNCTION__
#else
  #define FUNC_NAME
  #define LOOP
#endif

// Variadic templates:
// https://eli.thegreenplace.net/2014/variadic-templates-in-c/
template <typename T, typename... Args>
T* Alloc(Args&&... args) {
  NO_ROOTS_FRAME(FUNC_NAME);

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

// LayoutForwarded and LayoutFixed aren't real types.  You can cast arbitrary
// objs to them to access a HOMOGENEOUS REPRESENTATION useful for garbage
// collection.

class LayoutForwarded : public Obj {
 public:
  Obj* new_location;  // valid if and only if heap_tag_ == Tag::Forwarded
};

// for Tag::FixedSize
class LayoutFixed : public Obj {
 public:
  Obj* children_[16];  // only the entries denoted in field_mask will be valid
};

#endif  // GC_HEAP_H
