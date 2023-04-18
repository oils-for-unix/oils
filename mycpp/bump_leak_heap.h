// mycpp/bump_leak_heap.h: Leaky Bump Allocator

#ifndef MYCPP_BUMP_LEAK_HEAP_H
#define MYCPP_BUMP_LEAK_HEAP_H

#include <stdint.h>  // int64_t

#ifdef BUMP_ROOT
  #include <algorithm>  // max()
  #include <vector>
#endif

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

  // the BumpLeakHeap doesn't need rooting, but provide the option to
  // approximate its costs.
  void PushRoot(RawObject** p) {
#ifdef BUMP_ROOT
    roots_.push_back(p);
#endif
  }
  void PopRoot() {
#ifdef BUMP_ROOT
    roots_.pop_back();
#endif
  }

  void RootGlobalVar(void* root) {
  }

  void* Allocate(size_t num_bytes);
  void* Reallocate(void* p, size_t num_bytes);
  int MaybeCollect() {
#ifdef BUMP_ROOT
    // Do some computation with the roots
    max_roots_ = std::max(max_roots_, static_cast<int>(roots_.size()));
#endif
    return -1;  // no collection attempted
  }

  void PrintStats(int fd);

  void CleanProcessExit();
  void FastProcessExit();

  bool is_initialized_ = true;  // mark/sweep doesn't need to be initialized

  // In number of live objects, since we aren't keeping track of total bytes
  int gc_threshold_;
  int mem_pos_ = 0;

  // Cumulative stats
  int num_allocated_ = 0;
  int64_t bytes_allocated_ = 0;  // avoid overflow

#ifdef BUMP_ROOT
  std::vector<RawObject**> roots_;
  int max_roots_ = 0;
#endif
};

#ifdef BUMP_LEAK
extern BumpLeakHeap gHeap;
#endif

#endif  // MYCPP_BUMP_LEAK_HEAP_H
