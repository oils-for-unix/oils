#include "mycpp/runtime.h"

Heap gHeap;

// Disable 'new X' globally!
void* operator new(size_t size) {
  InvalidCodePath();
}

#ifdef MARK_SWEEP
  #include "mycpp/marksweep_heap.cc"
#else
  #include "mycpp/cheney_heap.cc"
#endif
