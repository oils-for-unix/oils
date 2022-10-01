#ifndef MARKSWEEP_H
#define MARKSWEEP_H

#include <new>
#include <unordered_set>
#include <vector>

class MarkSweepHeap {
  void MarkAllReferences(Obj* obj);

 public:
  MarkSweepHeap() {
  }
  void Init(int);

  void* Allocate(int);

  void PushRoot(Obj** p) {
    roots_.push_back(p);
  }

  void PopRoot() {
    roots_.pop_back();
  }

  void Collect();

  void Report(){};

  std::vector<Obj**> roots_;

  uint64_t current_heap_bytes_;
  uint64_t collection_thresh_;

  // TODO(Jesse): This should really be in an 'internal' build
  //
  bool is_initialized_ = true;  // mark/sweep doesn't need to be initialized

#if GC_STATS
  int num_live_objs_;
#endif

  std::vector<void*> all_allocations_;
  std::unordered_set<void*> marked_allocations_;
};

#endif
