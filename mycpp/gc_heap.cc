#include "mycpp/runtime.h"

Heap gHeap;

// Disable 'new X' globally!
void* operator new(size_t size) {
  InvalidCodePath();
}

// NOTE(Jesse): Put the implementations in header files because there's a
// special case script that copies all the _header_ files in mycpp to another
// directory.  It's the tarball script.
//
#ifdef MARK_SWEEP
  #include "mycpp/marksweep_heap_impl.h"
#else
  #include "mycpp/cheney_heap_impl.h"
#endif
