#ifndef MARKSWEEP_H
#define MARKSWEEP_H

#include <new>
#include <unordered_set>
#include <cstdint>

typedef uint64_t umm;

struct hashtable
{
  void **Elements;
  umm Count;
};



/* #define GC_STATS 1 */

// Implement hash and equality functors for unordered_set.
struct PointerHash {
  int operator() (const void* p) const {
    intptr_t i = reinterpret_cast<intptr_t>(p);
#if 1
    return i;
    //return i * 2654435761;
#else
    uint8_t* bytes = reinterpret_cast<uint8_t*>(&i);
#if 0
    log("%d", bytes[0]);
    log("%d", bytes[1]);
    log("%d", bytes[2]);
    log("%d", bytes[3]);
#endif

    int h = 0;
    h ^= bytes[0];
    h ^= bytes[1];
    h ^= bytes[2];
    h ^= bytes[3];

#if 1
    // DJB2 hash: http://www.cse.yorku.ca/~oz/hash.html
    int h = 5381;
    h = (h << 5) + h + bytes[0];
    h = (h << 5) + h + bytes[1];
    h = (h << 5) + h + bytes[2];
    h = (h << 5) + h + bytes[3];
#endif

    // log("h = %d bucket = %d", h, h % 128);
    //return i;
    return h;
    // return 0;
#endif
  }
};

struct PointerEquals {
  bool operator() (const void* x, const void* y) const {
    return x == y;
  }
};

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

  void Report(){};

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

  /* std::unordered_set<void*, PointerHash, PointerEquals> all_allocations_; */
  /* std::unordered_set<void*, PointerHash, PointerEquals> marked_allocations_; */

  hashtable all_allocations_;
  hashtable marked_allocations_;
};

#endif
