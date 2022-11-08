// mycpp/bump_leak_heap.cc: Leaky Bump Allocator

#include "mycpp/bump_leak_heap.h"

#include <stddef.h>
#include <stdio.h>

#include "mycpp/common.h"  // aligned

// We need this #ifdef because we don't want the global var in other binaries

#ifdef BUMP_LEAK
char gMemory[MiB(2000)];  // some benchmarks take more than 1 GiB

// This type is for "layout"; it's not instantiated
struct LayoutBlock {
  size_t num_bytes;
  char data[1];  // flexible array
};

// offsetof() accounts for possible padding, but it should equal sizeof(size_t)
const int kHeaderSize = offsetof(LayoutBlock, data);

// Allocate() bumps a pointer
void* BumpLeakHeap::Allocate(size_t num_bytes) {
  char* p = &(gMemory[mem_pos_]);
  LayoutBlock* block = reinterpret_cast<LayoutBlock*>(p);
  block->num_bytes = num_bytes;  // record size for Reallocate()

  mem_pos_ += aligned(kHeaderSize + num_bytes);

  // Update stats
  num_allocated_++;
  bytes_allocated_ += num_bytes;

  // log("Allocate() -> %p", block->data);
  return block->data;  // pointer user can write to
}

// Reallocate() calls Allocate() and then copies the old data
void* BumpLeakHeap::Reallocate(void* old_data, size_t num_bytes) {
  // log("");
  // log("Reallocate(%d) got %p", num_bytes, old_data);
  char* new_data = reinterpret_cast<char*>(Allocate(num_bytes));

  char* p_old = reinterpret_cast<char*>(old_data) - kHeaderSize;
  LayoutBlock* old_block = reinterpret_cast<LayoutBlock*>(p_old);

  memcpy(new_data, old_block->data, old_block->num_bytes);

  return new_data;
}

void BumpLeakHeap::Report() {
  log("[BumpLeakHeap]");
  log("  num allocated = %10d", num_allocated_);
  log("bytes allocated = %10d", bytes_allocated_);
  log("  mem pos       = %10d", mem_pos_);
}

BumpLeakHeap gHeap;
#endif
