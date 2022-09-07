#ifndef MARKSWEEP_H
#define MARKSWEEP_H

#include <new>
#include <unordered_set>

class MarkSweepHeap {
 public:
  MarkSweepHeap() {
  }
  void Init(int);

  void* Allocate(int);

  void MarkAllReferences(Obj* obj);

  void PushRoot(Obj** p) {
    assert(roots_top_ < kMaxRoots);
    roots_[roots_top_++] = p;
  }

  void PopRoot() {
    roots_top_--;
  }

  void Collect(int to_space_size = 0);

  int roots_top_;
  Obj** roots_[kMaxRoots];  // These are pointers to Obj* pointers

  uint64_t current_heap_bytes_;
  uint64_t collection_thresh_;

  // TODO(Jesse): This should really be in an 'internal' build
  //
  bool is_initialized_ = true; // mark/sweep doesn't need to be initialized

  std::unordered_set<void*> all_allocations_;
  std::unordered_set<void*> marked_allocations_;
};

#endif
