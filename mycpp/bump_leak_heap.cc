// mycpp/bump_leak_heap.cc: Leaky Bump Allocator

#include "mycpp/bump_leak_heap.h"

#include <stddef.h>
#include <stdio.h>

#include "mycpp/common.h"  // aligned

// We need this #ifdef because we don't want the global var in other binaries

#ifdef BUMP_LEAK
char gMemory[MiB(400)];  // 400 MiB of memory, zero'd

struct LayoutBlock {  // this type for "layout"; it's not instantiated
  size_t num_bytes;
  char data[1];  // flexible array
};

void* BumpLeakHeap::Allocate(size_t num_bytes) {
  char* p = &(gMemory[mem_pos_]);
  mem_pos_ += aligned(num_bytes);
  num_allocated_++;
  bytes_allocated_ += num_bytes;
  return p;
}

void* BumpLeakHeap::Reallocate(void* p, size_t num_bytes) {
  // TODO:
  // 1. Reserve 4 bytes for the size,
  // 2. Actually copy the data over to the new buffer!
  void* new_buffer = Allocate(num_bytes);
  return new_buffer;
}

void BumpLeakHeap::Report() {
  log("[BumpLeakHeap]");
  log("  num allocated = %10d", num_allocated_);
  log("bytes allocated = %10d", bytes_allocated_);
  log("  mem pos       = %10d", mem_pos_);
}

BumpLeakHeap gHeap;
#endif
