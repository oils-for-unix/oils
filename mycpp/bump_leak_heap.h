// mycpp/bump_leak_heap.h: Leaky Bump Allocator

#ifndef MYCPP_BUMP_LEAK_HEAP_H
#define MYCPP_BUMP_LEAK_HEAP_H

#include <stdint.h>  // int64_t

#include "mycpp/common.h"
#include "mycpp/gc_obj.h"

class BumpLeakHeap {
 public:
  // reserve 32 frames to start
  BumpLeakHeap() {
  }

  void Init() {
  }
  void Init(int gc_threshold) {
  }

  //
  // OLD Local Var Rooting
  //

  void PushRoot(Obj** p) {
  }

  void PopRoot() {
  }

  //
  // NEW Return Value Rooting
  //

  void RootOnReturn(Obj* root) {
  }

  void RootInCurrentFrame(Obj* root) {
  }

  void* Allocate(size_t num_bytes);
  void* Reallocate(void* p, size_t num_bytes);
  int Collect();
  void MarkObjects(Obj* obj);
  void Sweep();

  void CleanProcessExit() {
  }
  void FastProcessExit() {
    Report();
  }

  void Report();

  bool is_initialized_ = true;  // mark/sweep doesn't need to be initialized

  // In number of live objects, since we aren't keeping track of total bytes
  int gc_threshold_;
  int mem_pos_ = 0;

  // Cumulative stats
  int64_t num_allocated_ = 0;
  int64_t bytes_allocated_ = 0;
};

#if defined(BUMP_LEAK)
extern BumpLeakHeap gHeap;
#endif

#endif  // MYCPP_BUMP_LEAK_HEAP_H
