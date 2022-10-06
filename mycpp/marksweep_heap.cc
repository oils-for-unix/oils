#include "mycpp/runtime.h"

#define GC_VERBOSE 0

// Start of garbage collection.  We have a circular dependency here because I
// don't want some kind of STL iterator.
void RootSet::MarkRoots(MarkSweepHeap* heap) {
#if GC_VERBOSE
  log("Collect with %d roots and %d frames", NumRoots(), NumFrames());
#endif

  for (int i = 0; i < num_frames_; ++i) {
    const std::vector<Obj*>& frame = stack_[i];
    int n = frame.size();
    for (int j = 0; j < n; ++j) {
      // TODO: would be nice to do non-recursive marking
      heap->MarkObjects(frame[j]);
    }
  }
}

void MarkSweepHeap::Init() {
  Init(1000);  // collect at 1000 objects in tests
}

void MarkSweepHeap::Init(int collect_threshold) {
  collect_threshold_ = collect_threshold;
  live_objs_.reserve(KiB(10));
  roots_.reserve(KiB(1));  // prevent resizing in common case
}

void MarkSweepHeap::Report() {
  log("  num allocated   = %10d", num_allocated_);
  log("bytes allocated   = %10d", bytes_allocated_);
  log("  max live        = %10d", max_live_);
  log("  num live        = %10d", num_live_);
  log("  num collections = %10d", num_collections_);
  log("");
  log("roots capacity    = %10d", roots_.capacity());
  log(" objs capacity    = %10d", live_objs_.capacity());
}

void MarkSweepHeap::MaybePrintReport() {
  char* p = getenv("OIL_GC_STATS");
  if (p && strlen(p)) {
    Report();
  }
}

#ifdef MALLOC_LEAK

// for testing performance
void* MarkSweepHeap::Allocate(int num_bytes) {
  return calloc(num_bytes, 1);
}

#else

void* MarkSweepHeap::Allocate(int num_bytes) {
  RootsScope _r;  // TODO: could optimize this away with another method

  // log("Allocate %d", num_bytes);

  void* result = calloc(num_bytes, 1);
  assert(result);

  live_objs_.push_back(result);

  num_live_++;
  num_allocated_++;
  bytes_allocated_ += num_bytes;

  // Root BEFORE collection
  gHeap.RootOnReturn(static_cast<Obj*>(result));
  static_cast<Obj*>(result)->heap_tag_ = Tag::Opaque;  // it is opaque to start!

  #if GC_EVERY_ALLOC
  Collect();
  #else
  if (num_live_ > collect_threshold_) {
    Collect();
  }
  #endif

  // num_live_ updated after collection
  if (num_live_ > collect_threshold_) {
    collect_threshold_ = num_live_ * 2;
  }

  return result;
}

#endif  // MALLOC_LEAK

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

#define RETURN_ROOTING 1

int MarkSweepHeap::Collect() {
#if RETURN_ROOTING
  root_set_.MarkRoots(this);
#else
  int num_roots = roots_.size();
  for (int i = 0; i < num_roots; ++i) {
    // NOTE(Jesse): This is dereferencing again because I didn't want to
    // rewrite the stackroots class for this implementation.  Realistically we
    // should do that such that we don't store indirected pointers here.
    Obj* root = *(roots_[i]);

    if (root) {
      MarkObjects(root);
    }
  }
#endif

  Sweep();

  return num_live_;  // for unit tests only
}

// Cleanup at the end of main() to remain ASAN-safe
void MarkSweepHeap::OnProcessExit() {
  // Don't MarkObjects() because locals to main() are still live!  This must be
  // called right before main exits.
  root_set_.Clear();
  Sweep();
}

#if MARK_SWEEP
MarkSweepHeap gHeap;
#endif
