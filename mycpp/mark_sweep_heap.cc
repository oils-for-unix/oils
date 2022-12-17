#include <sys/time.h>  // gettimeofday()

#include "mycpp/runtime.h"

void MarkSweepHeap::Init() {
  Init(1000);  // collect at 1000 objects in tests
}

void MarkSweepHeap::Init(int gc_threshold) {
  gc_threshold_ = gc_threshold;

  char* e = getenv("OIL_GC_THRESHOLD");
  if (e) {
    int result;
    if (StringToInteger(e, strlen(e), 10, &result)) {
      // Override collection threshold
      gc_threshold_ = result;
    }
  }

  live_objs_.reserve(KiB(10));
  roots_.reserve(KiB(1));  // prevent resizing in common case
}

void MarkSweepHeap::Report() {
  log("  num allocated   = %10d", num_allocated_);
  log("bytes allocated   = %10d", bytes_allocated_);
  log("  max live        = %10d", max_live_);
  log("  num live        = %10d", num_live_);
  log("  num collections = %10d", num_collections_);
  log("   gc threshold   = %10d", gc_threshold_);
  log("");
  log("roots capacity    = %10d", roots_.capacity());
  log(" objs capacity    = %10d", live_objs_.capacity());
  log("");
  log("  max gc millis   = %10.1f", max_gc_millis_);
  log("total gc millis   = %10.1f", total_gc_millis_);
}

#if defined(MALLOC_LEAK)

// for testing performance
void* MarkSweepHeap::Allocate(size_t num_bytes) {
  return calloc(num_bytes, 1);
}

void* MarkSweepHeap::Reallocate(void* p, size_t num_bytes) {
  NotImplemented();
}

int MarkSweepHeap::MaybeCollect() {
  return -1;  // no collection
}

#elif defined(BUMP_LEAK)

#else

int MarkSweepHeap::MaybeCollect() {
  // Maybe collect BEFORE allocation, because the new object won't be rooted
  #if GC_EVERY_ALLOC
  int result = Collect();
  #else
  int result = -1;
  if (num_live_ > gc_threshold_) {
    result = Collect();
  }
  #endif

  // num_live_ UPDATED after possible collection
  if (num_live_ > gc_threshold_) {
    gc_threshold_ = num_live_ * 2;
  }

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

// Right now, this doesn't affect the GC policy
void* MarkSweepHeap::Reallocate(void* p, size_t num_bytes) {
  return realloc(p, num_bytes);
}

#endif  // MALLOC_LEAK

// The "homogeneous" layout of objects with Tag::FixedSize.  LayoutFixed is for
// casting; it isn't a real type.

class LayoutFixed : public Obj {
 public:
  Obj* children_[16];  // only the entries denoted in field_mask will be valid
};

void MarkSweepHeap::MarkObjects(Obj* obj) {
  bool is_marked = marked_.find(obj) != marked_.end();
  if (is_marked) {
    return;
  }

  marked_.insert(static_cast<void*>(obj));

  auto header = ObjHeader(obj);
  switch (header->heap_tag_) {
  case Tag::FixedSize: {
    auto fixed = reinterpret_cast<LayoutFixed*>(header);
    int mask = fixed->field_mask_;

    // TODO(Jesse): Put the 16 in a #define
    for (int i = 0; i < 16; ++i) {
      if (mask & (1 << i)) {
        Obj* child = fixed->children_[i];
        if (child) {
          MarkObjects(child);
        }
      }
    }

    break;
  }

  case Tag::Scanned: {
    assert(header == obj);

    auto slab = reinterpret_cast<Slab<void*>*>(header);

    // TODO(Jesse): Give this a name
    int n = (slab->obj_len_ - kSlabHeaderSize) / sizeof(void*);

    for (int i = 0; i < n; ++i) {
      Obj* child = reinterpret_cast<Obj*>(slab->items_[i]);
      if (child) {
        MarkObjects(child);
      }
    }

    break;
  }

  default: {
    assert(header->heap_tag_ == Tag::Forwarded ||
           header->heap_tag_ == Tag::Global ||
           header->heap_tag_ == Tag::Opaque);
  }

    // other tags like Tag::Opaque have no children
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
  max_live_ = std::max(max_live_, num_live_);
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

#ifdef GC_VERBOSE
  log("%2d. GC with %d roots (%d global) and %d live objects", num_collections_,
      num_roots + num_globals, num_globals, num_live_);
#endif

  // Note: Can we get rid of double pointers?

  for (int i = 0; i < num_roots; ++i) {
    Obj* root = *(roots_[i]);
    if (root) {
      MarkObjects(root);
    }
  }

  for (int i = 0; i < num_globals; ++i) {
    Obj* root = global_roots_[i];
    if (root) {
      MarkObjects(root);
    }
  }

  Sweep();
#ifdef GC_VERBOSE
  log("    %d live after sweep", num_live_);
#endif

#ifdef GC_TIMING
  if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &end) < 0) {
    assert(0);
  }

  double start_secs = start.tv_sec + start.tv_nsec / 1e9;
  double end_secs = end.tv_sec + end.tv_nsec / 1e9;
  double gc_millis = (end_secs - start_secs) * 1000.0;

  #ifdef GC_VERBOSE
  log("    %.1f ms GC", gc_millis);
  #endif
#endif

  total_gc_millis_ += gc_millis;
  if (gc_millis > max_gc_millis_) {
    max_gc_millis_ = gc_millis;
  }

  return num_live_;  // for unit tests only
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

  e = getenv("OIL_GC_STATS");
  if (e && strlen(e)) {  // env var set and non-empty
    Report();
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
