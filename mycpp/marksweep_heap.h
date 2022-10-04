#ifndef MARKSWEEP_H
#define MARKSWEEP_H

#include <unordered_set>
#include <vector>

class MarkSweepHeap {
  void MarkAllReferences(Obj* obj);

 public:
  MarkSweepHeap() {
  }

  void Init();  // default threshold
  void Init(int collect_threshold);

  void* Allocate(int num_bytes);

  void PushRoot(Obj** p) {
    roots_.push_back(p);
  }

  void PopRoot() {
    roots_.pop_back();
  }

  void Collect();

  void MaybePrintReport();
  void Report();

  // TODO(Jesse): This should really be in an 'internal' build
  bool is_initialized_ = true;  // mark/sweep doesn't need to be initialized

  // In number of allocations, since we aren't keeping track of total bytes
  int64_t collect_threshold_;

  // Cumulative stats
  int64_t num_allocated_ = 0;
  int64_t bytes_allocated_ = 0;
  int64_t num_collections_ = 0;

  // current stats
  int64_t num_live_ = 0;
  // Should we keep track of sizes?
  // int64_t bytes_live_ = 0;

  std::vector<Obj**> roots_;
  std::vector<void*> all_allocations_;
  std::unordered_set<void*> marked_allocations_;
};

#endif
