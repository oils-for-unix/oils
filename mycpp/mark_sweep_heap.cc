#include "mycpp/mark_sweep_heap.h"

#include <inttypes.h>  // PRId64
#include <stdlib.h>    // getenv()
#include <string.h>    // strlen()
#include <sys/time.h>  // gettimeofday()
#include <time.h>      // clock_gettime(), CLOCK_PROCESS_CPUTIME_ID
#include <unistd.h>    // STDERR_FILENO

#include "_build/detected-cpp-config.h"  // for GC_TIMING
#include "mycpp/gc_builtins.h"           // StringToInteger()
#include "mycpp/gc_slab.h"

// TODO: Remove this guard when we have separate binaries
#if MARK_SWEEP

void MarkSweepHeap::Init() {
  Init(1000);  // collect at 1000 objects in tests
}

void MarkSweepHeap::Init(int gc_threshold) {
  gc_threshold_ = gc_threshold;

  char* e;
  e = getenv("OIL_GC_THRESHOLD");
  if (e) {
    int result;
    if (StringToInteger(e, strlen(e), 10, &result)) {
      // Override collection threshold
      gc_threshold_ = result;
    }
  }

  // only for developers
  e = getenv("_OIL_GC_VERBOSE");
  if (e && strcmp(e, "1") == 0) {
    gc_verbose_ = true;
  }

  live_objs_.reserve(KiB(10));
  roots_.reserve(KiB(1));  // prevent resizing in common case
}

int MarkSweepHeap::MaybeCollect() {
  // Maybe collect BEFORE allocation, because the new object won't be rooted
  #if GC_ALWAYS
  int result = Collect();
  #else
  int result = -1;
  if (num_live_ > gc_threshold_) {
    result = Collect();
  }
  #endif

  num_gc_points_++;  // this is a manual collection point
  return result;
}

// Allocate and update stats
void* MarkSweepHeap::Allocate(size_t num_bytes) {
  // log("Allocate %d", num_bytes);

  if (to_free_.empty()) {
    // Use higher object IDs
    obj_id_after_allocate_ = greatest_obj_id_;
    greatest_obj_id_++;

    // This check is ON in release mode
    CHECK(greatest_obj_id_ <= kMaxObjId);

  } else {
    RawObject* dead = to_free_.back();
    to_free_.pop_back();

    ObjHeader* header = FindObjHeader(dead);
    obj_id_after_allocate_ = header->obj_id;  // reuse the dead object's ID

    free(dead);
  }

  void* result = calloc(num_bytes, 1);
  DCHECK(result != nullptr);

  live_objs_.push_back(reinterpret_cast<RawObject*>(result));

  num_live_++;
  num_allocated_++;
  bytes_allocated_ += num_bytes;

  return result;
}

  #if 0
void* MarkSweepHeap::Reallocate(void* p, size_t num_bytes) {
  FAIL(kNotImplemented);
  // This causes a double-free in the GC!
  // return realloc(p, num_bytes);
}
  #endif

// "Leaf" for marking / TraceChildren
//
// - Abort if nullptr
// - Find the header (get rid of this when remove ObjHeader member)
// - Tag::{Opaque,FixedSized,Scanned} have their mark bits set
// - Tag::{FixedSize,Scanned} are also pushed on the gray stack

void MarkSweepHeap::MaybeMarkAndPush(RawObject* obj) {
  ObjHeader* header = FindObjHeader(obj);
  int obj_id = header->obj_id;

  // Don't re-mark or re-push
  if (mark_set_.IsMarked(obj_id)) {
    return;
  }

  switch (header->heap_tag) {
  case HeapTag::Opaque:  // e.g. strings have no children
    mark_set_.Mark(obj_id);
    break;

  case HeapTag::Scanned:  // these 2 types have children
  case HeapTag::FixedSize:
    mark_set_.Mark(obj_id);
    gray_stack_.push_back(header);  // Push the header, not the object!
    break;

  case HeapTag::Global:  // don't mark or push
    break;

  default:
    FAIL(kShouldNotGetHere);
  }
}

void MarkSweepHeap::TraceChildren() {
  while (!gray_stack_.empty()) {
    ObjHeader* header = gray_stack_.back();
    gray_stack_.pop_back();

    switch (header->heap_tag) {
    case HeapTag::FixedSize: {
      auto fixed = reinterpret_cast<LayoutFixed*>(header);
      int mask = FIELD_MASK(fixed->header_);

      for (int i = 0; i < kFieldMaskBits; ++i) {
        if (mask & (1 << i)) {
          RawObject* child = fixed->children_[i];
          if (child) {
            MaybeMarkAndPush(child);
          }
        }
      }
      break;
    }

    case HeapTag::Scanned: {
      // no vtable
      // assert(reinterpret_cast<void*>(header) ==
      // reinterpret_cast<void*>(obj));

      auto slab = reinterpret_cast<Slab<RawObject*>*>(header);

      int n = NUM_POINTERS(slab->header_);
      for (int i = 0; i < n; ++i) {
        RawObject* child = slab->items_[i];
        if (child) {
          MaybeMarkAndPush(child);
        }
      }
      break;
    }
    default:
      // Only FixedSize and Scanned are pushed
      FAIL(kShouldNotGetHere);
    }
  }
}

void MarkSweepHeap::Sweep() {
  int last_live_index = 0;
  int num_objs = live_objs_.size();
  for (int i = 0; i < num_objs; ++i) {
    RawObject* obj = live_objs_[i];
    assert(obj);  // malloc() shouldn't have returned nullptr

    ObjHeader* header = FindObjHeader(obj);
    bool is_live = mark_set_.IsMarked(header->obj_id);

    // Compact live_objs_ and populate to_free_.  Note: doing the reverse could
    // be more efficient when many objects are dead.
    if (is_live) {
      live_objs_[last_live_index++] = obj;
    } else {
      to_free_.push_back(obj);
      // free(obj);
      num_live_--;
    }
  }
  live_objs_.resize(last_live_index);  // remove dangling objects

  num_collections_++;
  max_survived_ = std::max(max_survived_, num_live_);
}

int MarkSweepHeap::Collect() {
  #ifdef GC_TIMING
  struct timespec start, end;
  if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &start) < 0) {
    assert(0);
  }
  #endif

  int num_roots = roots_.size();
  int num_globals = global_roots_.size();

  if (gc_verbose_) {
    log("");
    log("%2d. GC with %d roots (%d global) and %d live objects",
        num_collections_, num_roots + num_globals, num_globals, num_live_);
  }

  // Resize it
  mark_set_.ReInit(greatest_obj_id_);

  // Mark roots.
  // Note: It might be nice to get rid of double pointers
  for (int i = 0; i < num_roots; ++i) {
    RawObject* root = *(roots_[i]);
    if (root) {
      MaybeMarkAndPush(root);
    }
  }

  for (int i = 0; i < num_globals; ++i) {
    RawObject* root = global_roots_[i];
    if (root) {
      MaybeMarkAndPush(root);
    }
  }

  // Traverse object graph.
  TraceChildren();

  Sweep();

  if (gc_verbose_) {
    log("    %d live after sweep", num_live_);
  }

  // We know how many are live.  If the number of objects is close to the
  // threshold (above 75%), then set the threshold to 2 times the number of
  // live objects.  This is an ad hoc policy that removes observed "thrashing"
  // -- being at 99% of the threshold and doing FUTILE mark and sweep.

  int water_mark = (gc_threshold_ * 3) / 4;
  if (num_live_ > water_mark) {
    gc_threshold_ = num_live_ * 2;
    num_growths_++;
    if (gc_verbose_) {
      log("    exceeded %d live objects; gc_threshold set to %d", water_mark,
          gc_threshold_);
    }
  }

  #ifdef GC_TIMING
  if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &end) < 0) {
    assert(0);
  }

  double start_secs = start.tv_sec + start.tv_nsec / 1e9;
  double end_secs = end.tv_sec + end.tv_nsec / 1e9;
  double gc_millis = (end_secs - start_secs) * 1000.0;

  if (gc_verbose_) {
    log("    %.1f ms GC", gc_millis);
  }

  total_gc_millis_ += gc_millis;
  if (gc_millis > max_gc_millis_) {
    max_gc_millis_ = gc_millis;
  }
  #endif

  return num_live_;  // for unit tests only
}

void MarkSweepHeap::PrintStats(int fd) {
  dprintf(fd, "  num live        = %10d\n", num_live_);
  // max survived_ can be less than num_live_, because leave off the last GC
  dprintf(fd, "  max survived    = %10d\n", max_survived_);
  dprintf(fd, "\n");
  dprintf(fd, "  num allocated   = %10d\n", num_allocated_);
  dprintf(fd, "bytes allocated   = %10" PRId64 "\n", bytes_allocated_);
  dprintf(fd, "\n");
  dprintf(fd, "  num gc points   = %10d\n", num_gc_points_);
  dprintf(fd, "  num collections = %10d\n", num_collections_);
  dprintf(fd, "\n");
  dprintf(fd, "   gc threshold   = %10d\n", gc_threshold_);
  dprintf(fd, "  num growths     = %10d\n", num_growths_);
  dprintf(fd, "\n");
  dprintf(fd, "  max gc millis   = %10.1f\n", max_gc_millis_);
  dprintf(fd, "total gc millis   = %10.1f\n", total_gc_millis_);
  dprintf(fd, "\n");
  dprintf(fd, "roots capacity    = %10d\n",
          static_cast<int>(roots_.capacity()));
  dprintf(fd, " objs capacity    = %10d\n",
          static_cast<int>(live_objs_.capacity()));
}

void MarkSweepHeap::EagerFree() {
  for (auto obj : to_free_) {
    free(obj);
  }
}

// Cleanup at the end of main() to remain ASAN-safe
void MarkSweepHeap::DoProcessExit(bool fast_exit) {
  char* e = getenv("OIL_GC_ON_EXIT");

  if (fast_exit) {
    // don't collect by default; OIL_GC_ON_EXIT=1 overrides
    if (e && strcmp(e, "1") == 0) {
      Collect();
      EagerFree();
    }
  } else {
    // collect by default; OIL_GC_ON_EXIT=0 overrides
    if (e && strcmp(e, "0") == 0) {
      ;
    } else {
      Collect();
      EagerFree();
    }
  }

  int stats_fd = -1;
  e = getenv("OIL_GC_STATS");
  if (e && strlen(e)) {  // env var set and non-empty
    stats_fd = STDERR_FILENO;
  } else {
    // A raw file descriptor lets benchmarks extract stats even if the script
    // writes to stdout and stderr.  Shells can't use open() without potential
    // conflicts.

    e = getenv("OIL_GC_STATS_FD");
    if (e && strlen(e)) {
      // Try setting 'stats_fd'.  If there's an error, it will be unchanged, and
      // we don't PrintStats();
      StringToInteger(e, strlen(e), 10, &stats_fd);
    }
  }

  if (stats_fd != -1) {
    PrintStats(stats_fd);
  }
}

void MarkSweepHeap::CleanProcessExit() {
  DoProcessExit(false);  // not fast_exit
}

// for the main binary
void MarkSweepHeap::FastProcessExit() {
  DoProcessExit(true);
}

MarkSweepHeap gHeap;

#endif  // MARK_SWEEP
