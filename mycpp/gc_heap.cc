#error "This file should never be compiled .. and yet .."

#if 0
#include "mycpp/runtime.h"

Heap gHeap;

// Disable 'new X' globally!
//
// NOTE(Jesse): Inserting elements into unordered_set calls `new` internally so
// we have to either figure out how to coerce it into either accepting the gc'd
// allocator (if that's even a plausible path) or disallowing new is not possible.
//
// Alternatively, we could write our own hashtable, which is pretty easy.
//
#if 0
void* operator new(size_t size) {
  InvalidCodePath();
}
#endif

// NOTE(Jesse): Put the implementations in header files because there's a
// special case script that copies all the _header_ files in mycpp to another
// directory.  It's the tarball script.
//
#ifdef MARK_SWEEP
  #include "mycpp/marksweep_heap_impl.h"
#else
  #include "mycpp/cheney_heap_impl.h"
#endif
#endif
