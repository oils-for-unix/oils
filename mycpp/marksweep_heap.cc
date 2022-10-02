#include "mycpp/runtime.h"

void MarkSweepHeap::Init(int collection_thresh) {
  collection_thresh_ = collection_thresh;
  all_allocations_.reserve(KiB(10));
  roots_.reserve(KiB(1));  // prevent resizing in common case
}

#ifdef MALLOC_LEAK

// for testing performance
void* MarkSweepHeap::Allocate(int byte_count) {
  return calloc(byte_count, 1);
}

#else

void* MarkSweepHeap::Allocate(int byte_count) {
  #if GC_EVERY_ALLOC
  Collect();
  #endif

  #if GC_STATS
  num_live_objs_++;
  #endif

  current_heap_bytes_ += byte_count;
  if (current_heap_bytes_ > collection_thresh_) {
    Collect();
  }

  // TODO: collection policy isn't correct, as current_heap_bytes_ isn't
  // updated on collection.

  if (current_heap_bytes_ > collection_thresh_) {
    //
    // NOTE(Jesse): Generally, doubling results in a lot of wasted space.  I've
    // observed growing by a factor of 1.5x, or even 1.3x, to be a good
    // time/space tradeoff in the past.  Unclear if that's good for a typical
    // Oil workload, but we've got to start somewhere.
    //
    // 1.5x = (3/2)
    // 1.3x = (13/10)
    //
    collection_thresh_ = current_heap_bytes_ * 3 / 2;
  }

  void* result = calloc(byte_count, 1);
  assert(result);

  all_allocations_.push_back(result);

  return result;
}

#endif  // MALLOC_LEAK

void MarkSweepHeap::MarkAllReferences(Obj* obj) {
  auto header = ObjHeader(obj);

  auto marked_alloc = marked_allocations_.find((Obj*)obj);
  bool alloc_is_marked = marked_alloc != marked_allocations_.end();
  if (alloc_is_marked) {
    return;
  }

  marked_allocations_.insert(static_cast<void*>(obj));

  switch (header->heap_tag_) {
  case Tag::FixedSize: {
    auto fixed = reinterpret_cast<LayoutFixed*>(header);
    int mask = fixed->field_mask_;

    // TODO(Jesse): Put the 16 in a #define
    for (int i = 0; i < 16; ++i) {
      if (mask & (1 << i)) {
        Obj* child = fixed->children_[i];
        if (child) {
          MarkAllReferences(child);
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
        MarkAllReferences(child);
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

void MarkSweepHeap::Collect() {
  int num_roots = roots_.size();
  for (int i = 0; i < num_roots; ++i) {
    // NOTE(Jesse): This is dereferencing again because I didn't want to
    // rewrite the stackroots class for this implementation.  Realistically we
    // should do that such that we don't store indirected pointers here.
    Obj* root = *(roots_[i]);

    if (root) {
      MarkAllReferences(root);
    }
  }

  int last_live_index = 0;
  int num_objs = all_allocations_.size();
  for (int alloc_index = 0; alloc_index < num_objs; ++alloc_index) {
    void* alloc = all_allocations_[alloc_index];
    assert(alloc);  // malloc() shouldn't have returned nullptr

    auto marked_alloc = marked_allocations_.find(alloc);
    bool alloc_is_live = marked_alloc != marked_allocations_.end();

    if (alloc_is_live) {
      all_allocations_[last_live_index++] = alloc;
    } else {
      free(alloc);

#if GC_STATS
      num_live_objs_--;
#endif
    }
  }

  all_allocations_.resize(last_live_index);
  marked_allocations_.clear();
}

#if MARK_SWEEP
MarkSweepHeap gHeap;
#endif
