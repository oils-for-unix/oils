#include "mycpp/runtime.h"

void MarkSweepHeap::Init(int collection_thresh) {
  this->collection_thresh_ = collection_thresh;
}

void* MarkSweepHeap::Allocate(int byte_count) {

#if GC_EVERY_ALLOC
  Collect();
#endif

#if GC_STATS
  this->num_live_objs_++;
#endif


  this->current_heap_bytes_ += byte_count;
  if (this->current_heap_bytes_ > this->collection_thresh_) {
    Collect();
  }

  // TODO: collection policy isn't correct, as this->current_heap_bytes_ isn't
  // updated on collection.

  if (this->current_heap_bytes_ > this->collection_thresh_) {
    //
    // NOTE(Jesse): Generally, doubling results in a lot of wasted space.  I've
    // observed growing by a factor of 1.5x, or even 1.3x, to be a good
    // time/space tradeoff in the past.  Unclear if that's good for a typical
    // Oil workload, but we've got to start somewhere.
    //
    // 1.5x = (3/2)
    // 1.3x = (13/10)
    //
    this->collection_thresh_ = this->current_heap_bytes_ * 3 / 2;
  }

  void* result = calloc(byte_count, 1);
  assert(result);

  this->all_allocations_.insert(result);

  return result;
}

void MarkSweepHeap::MarkAllReferences(Obj* obj) {
  auto header = ObjHeader(obj);

  this->marked_allocations_.insert(static_cast<void*>(obj));

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
  for (int root_index = 0; root_index < this->roots_top_; ++root_index) {
    // NOTE(Jesse): This is dereferencing again because I didn't want to
    // rewrite the stackroots class for this implementation.  Realistically we
    // should do that such that we don't store indirected pointers here.
    Obj* root = *(this->roots_[root_index]);

    if (root) {
      MarkAllReferences(root);
    }
  }

  for (auto it = all_allocations_.begin(); it != all_allocations_.end(); ++it) {
    void* alloc = *it;

    auto marked_alloc = marked_allocations_.find(alloc);
    bool alloc_is_dead = marked_alloc == marked_allocations_.end();

    if (alloc_is_dead) {
      free(alloc);

#if GC_STATS
      this->num_live_objs_--;
#endif
    }
  }

  all_allocations_.clear();

  for (auto it = marked_allocations_.begin(); it != marked_allocations_.end();
       ++it) {
    Obj* obj = reinterpret_cast<Obj*>(*it);
    if (obj->heap_tag_ != Tag::Global) {
      all_allocations_.insert(*it);
    }
  }

  marked_allocations_.clear();
}

#if MARK_SWEEP
MarkSweepHeap gHeap;
#endif
