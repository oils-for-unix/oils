#include "mycpp/runtime.h"

Heap gHeap;

// Disable 'new X' globally!
void* operator new(size_t size) {
  InvalidCodePath();
}

#ifdef MARK_SWEEP
  #include "marksweep_heap.cc"
#else
  #include "cheney_heap.cc"
#endif

