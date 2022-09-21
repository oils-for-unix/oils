#ifndef MARKSWEEP_H
#define MARKSWEEP_H

#include <new>
#include <unordered_set>

class MarkSweepHeap {
  void MarkAllReferences(Obj* obj);

 public:
  MarkSweepHeap() {
  }
  void Init(int);

  void* Allocate(int);

  void PushRoot(Obj** p) {
    assert(roots_top_ < kMaxRoots);
    roots_[roots_top_++] = p;
  }

  void PopRoot() {
    roots_top_--;
  }

  void Collect();

  void Report() {};

  int roots_top_;
  Obj** roots_[kMaxRoots];  // These are pointers to Obj* pointers

  uint64_t current_heap_bytes_;
  uint64_t collection_thresh_;

  // TODO(Jesse): This should really be in an 'internal' build
  //
  bool is_initialized_ = true;  // mark/sweep doesn't need to be initialized

#if GC_STATS
  int num_live_objs_;
#endif

  std::unordered_set<void*> all_allocations_;
  std::unordered_set<void*> marked_allocations_;
};

#endif
