#include <inttypes.h>  // PRId64
#include <sys/time.h>  // gettimeofday()
#include <time.h>      // clock_gettime(), CLOCK_PROCESS_CPUTIME_ID
#include <unistd.h>    // STDERR_FILENO

#include "_build/detected-cpp-config.h"  // for GC_TIMING
#include "mycpp/runtime.h"

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

#if defined(MALLOC_LEAK)

// for testing performance
void* MarkSweepHeap::Allocate(size_t num_bytes) {
  return calloc(num_bytes, 1);
}

void* MarkSweepHeap::Reallocate(void* p, size_t num_bytes) {
  FAIL(kNotImplemented);
}

int MarkSweepHeap::MaybeCollect() {
  return -1;  // no collection
}

#elif defined(BUMP_LEAK)

#else

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

void* MarkSweepHeap::Allocate(size_t num_bytes) {
  // log("Allocate %d", num_bytes);

  //
  // Allocate and update stats
  //

  void* result = calloc(num_bytes, 1);
  assert(result);

  live_objs_.push_back(result);

  num_live_++;
  num_allocated_++;
  bytes_allocated_ += num_bytes;

  return result;
}

void* MarkSweepHeap::Reallocate(void* p, size_t num_bytes) {
  FAIL(kNotImplemented);
  // This causes a double-free in the GC!
  // return realloc(p, num_bytes);
}

#endif  // MALLOC_LEAK

void MarkSweepHeap::MarkObjects(RawObject* obj) {
  bool is_marked = marked_.find(obj) != marked_.end();
  if (is_marked) {
    return;
  }

  auto header = FindObjHeader(obj);
  switch (header->heap_tag) {
  case HeapTag::Opaque:
    marked_.insert(obj);
    break;

  case HeapTag::FixedSize: {
    marked_.insert(obj);

    auto fixed = reinterpret_cast<LayoutFixed*>(header);
    int mask = fixed->header_.field_mask;

    // TODO(Jesse): Put the 16 in a #define
    for (int i = 0; i < 16; ++i) {
      if (mask & (1 << i)) {
        RawObject* child = fixed->children_[i];
        if (child) {
          MarkObjects(child);
        }
      }
    }
    break;
  }

  case HeapTag::Scanned: {
    marked_.insert(obj);

    // no vtable
    assert(reinterpret_cast<void*>(header) == reinterpret_cast<void*>(obj));

    auto slab = reinterpret_cast<Slab<RawObject*>*>(header);

    // TODO: mark and sweep should store number of pointers directly
    int n = (slab->header_.obj_len - kSlabHeaderSize) / sizeof(void*);

    for (int i = 0; i < n; ++i) {
      RawObject* child = slab->items_[i];
      if (child) {
        MarkObjects(child);
      }
    }
    break;
  }

  case HeapTag::Global:
    // Not marked
    break;

  default:
    // Invalid tag
    assert(0);
  }
}

void MarkSweepHeap::Sweep() {
  int last_live_index = 0;
  int num_objs = live_objs_.size();
  for (int i = 0; i < num_objs; ++i) {
    void* obj = live_objs_[i];
    assert(obj);  // malloc() shouldn't have returned nullptr

    bool is_live = marked_.find(obj) != marked_.end();
    if (is_live) {
      live_objs_[last_live_index++] = obj;
    } else {
      free(obj);
      num_live_--;
    }
  }
  live_objs_.resize(last_live_index);  // remove dangling objects
  marked_.clear();

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

  // Note: Can we get rid of double pointers?

  for (int i = 0; i < num_roots; ++i) {
    RawObject* root = *(roots_[i]);
    if (root) {
      MarkObjects(root);
    }
  }

  for (int i = 0; i < num_globals; ++i) {
    RawObject* root = global_roots_[i];
    if (root) {
      MarkObjects(root);
    }
  }

#if 0
  log("Collect(): num marked %d", marked_.size());
  for (auto marked_obj : marked_ ) {
    auto m = reinterpret_cast<RawObject*>(marked_obj);
    assert(m->heap_tag != HeapTag::Global);  // BUG FIX
  }
#endif

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

// Cleanup at the end of main() to remain ASAN-safe
void MarkSweepHeap::DoProcessExit(bool fast_exit) {
  char* e = getenv("OIL_GC_ON_EXIT");

  if (fast_exit) {
    // don't collect by default; OIL_GC_ON_EXIT=1 overrides
    if (e && strcmp(e, "1") == 0) {
      Collect();
    }
  } else {
    // collect by default; OIL_GC_ON_EXIT=0 overrides
    if (e && strcmp(e, "0") == 0) {
      ;
    } else {
      Collect();
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

#if defined(MARK_SWEEP) && !defined(BUMP_LEAK)
MarkSweepHeap gHeap;
#endif
