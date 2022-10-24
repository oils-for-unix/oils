// mycpp/bump_alloc.cc: Leaky Bump Allocator

#include "mycpp/bump_alloc.h"

#include <stddef.h>
#include <stdio.h>

#include "mycpp/common.h"  // aligned

// We need this #ifdef because we don't want the global var in other binaries

#ifdef BUMP_LEAK
char gMemory[MiB(400)];  // 400 MiB of memory, zero'd

void* BumpLeakHeap::Allocate(int num_bytes) {
  char* p = &(gMemory[mem_pos_]);
  #ifdef ALLOC_LOG
  printf("alloc %zu\n", num_bytes);
  #endif
  mem_pos_ += aligned(num_bytes);
  num_allocated_++;
  bytes_allocated_ += num_bytes;
  return p;
}

void BumpLeakHeap::Report() {
  log("[BumpLeakHeap]");
  log("  num allocated = %10d", num_allocated_);
  log("bytes allocated = %10d", bytes_allocated_);
  log("  mem pos       = %10d", mem_pos_);
}

BumpLeakHeap gHeap;
#endif
