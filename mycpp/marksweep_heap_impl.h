void Heap::Init(int max_heap_bytes) {
  this->max_heap_bytes = max_heap_bytes;
}

void* Heap::Allocate(int byte_count) {
  void* Result = calloc(byte_count, 1);
  assert(Result);

  /* this->AllAllocations.insert(Result); */

  this->current_heap_bytes += byte_count;
  if (this->current_heap_bytes > this->max_heap_bytes) {
    Collect();
  }

  if (this->current_heap_bytes > this->max_heap_bytes) {
    // NOTE(Jesse): Generally, doubling results in a lot of wasted space.  I've
    // observed growing by a factor of 1.5x, or even 1.3x, to be a good
    // time-space tradeoff.
    //
    // 1.5x = (3/2)
    // 1.3x = (13/10)
    //
    int growth_factor = (3 / 2);
    this->max_heap_bytes = this->current_heap_bytes * growth_factor;
  }

  return Result;
}

void Heap::MarkAllReferences(Obj* obj) {
#if 0
  auto header = ObjHeader(obj);

  this->MarkedAllocations.insert(Obj);

  switch (header->heap_tag_) {
  case Tag::FixedSize: {
    auto fixed = reinterpret_cast<LayoutFixed*>(header);
    int mask = fixed->field_mask_;
    for (int i = 0; i < 16; ++i) {
      if (mask & (1 << i)) {
        Obj* child = fixed->children_[i];
        // log("i = %d, p = %p, heap_tag = %d", i, child, child->heap_tag_);
        if (child) {
          auto child_header = ObjHeader(child);
          // log("  fixed: child %d from %p", i, child);
          fixed->children_[i] = MarkAllReferences(child, child_header);
          // log("  to %p", fixed->children_[i]);
        }
      }
    }
    break;
  }
  case Tag::Scanned: {
    assert(header == obj);  // no inheritance
    auto slab = reinterpret_cast<Slab<void*>*>(header);
    int n = (slab->obj_len_ - kSlabHeaderSize) / sizeof(void*);
    for (int i = 0; i < n; ++i) {
      Obj* child = reinterpret_cast<Obj*>(slab->items_[i]);
      if (child) {  // note: List<> may have nullptr; Dict is sparse
        auto child_header = ObjHeader(child);
        slab->items_[i] = MarkAllReferences(child, child_header);
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
  // aligned() like Heap::Allocate()
  scan += aligned(header->obj_len_);
#endif
}

void Heap::Collect(int byte_count) {
  for (int root_index = 0; root_index < this->roots_top_; ++root_index) {
    // NOTE(Jesse): This is dereferencing again because I didn't want to
    // rewrite the stackroots class for this implementation.  Realistically we
    // should do that such that we don't store indirected pointers here.
    Obj* Root = this->roots_[root_index][0];

    MarkAllReferences(Root);

    for (auto it = AllAllocations.begin(); it != AllAllocations.end(); ++it) {
    }
  }
}
