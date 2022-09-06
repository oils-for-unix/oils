#ifndef MARKSWEEP_H
#define MARKSWEEP_H

#include <new>
#include <unordered_set>

const int kMaxRoots = Kilobytes(4);

typedef uint64_t u64;

class Heap {
 public:
  Heap() {
  }
  void Init(int space_size);

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

  u64 current_heap_bytes;
  u64 max_heap_bytes;

  // TODO(Jesse): This should really be in an 'internal' build
  bool is_initialized_ =
      true;  // mark/sweep heap doesn't need to be initialized

  std::unordered_set<void*> AllAllocations;
  std::unordered_set<void*> MarkedAllocations;
};

#endif
