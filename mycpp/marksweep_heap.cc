#include "mycpp/runtime.h"

uint64_t
Hash(void* Value)
{
  /* uint64_t Result = (uint64_t)Value * 2654435761; */
  uint64_t Result = (uint64_t)Value;
  /* uint64_t Result = 0; */
  return Result;
}

void **
GetBucketFor(hashtable *Table, umm HashValue)
{
  umm BucketIndex = HashValue % Table->Count;
  void **Result = Table->Elements + BucketIndex;
  return Result;
}

bool
NotEmpty(void** Bucket)
{
  bool Result = *Bucket != 0;
  return Result;
}


void
AllocateHashtable(hashtable *Table, int Count)
{
  Table->Count = Count;
  Table->Elements = (void**)calloc(Count, sizeof(void*));
}

bool
HashtableContains(hashtable *Table, void *Value)
{
  uint64_t HashValue = Hash(Value);
  void **Bucket = GetBucketFor(Table, HashValue);

  void **FirstBucket = Bucket;

  umm CollisionCount = 0;
  while (NotEmpty(Bucket) && *Bucket != Value)
  {
    CollisionCount++;
    HashValue++;

    Bucket = GetBucketFor(Table, HashValue);

    if (Bucket == FirstBucket) { Bucket = 0; break; }
  }

  /* if (CollisionCount > 3) */
  /* { */
  /*   log("%u collisions on lookup (%p)", CollisionCount, Value); */
  /* } */

  bool Result = (Bucket && *Bucket == Value);
  return Result;
}

void
HashtableInsert(hashtable *Table, void *insertValue)
{
  assert(insertValue != 0);

  uint64_t HashValue = Hash(insertValue);
  void **Bucket = GetBucketFor(Table, HashValue);

  void **FirstBucket = Bucket;

  umm CollisionCount = 0;
  while (NotEmpty(Bucket))
  {
    CollisionCount++;
    HashValue++;

    Bucket = GetBucketFor(Table, HashValue);

    if (Bucket == FirstBucket) { Bucket = 0; log("insertion failed; hashtable full"); break; }
  }

  /* if (CollisionCount > 3) */
  /* { */
  /*   log("%u collision on insert (%p)", CollisionCount, insertValue); */
  /* } */

  if (Bucket)
  {
    *Bucket = insertValue;
  }
}

void
HashtableClear(hashtable *Table)
{
  for (umm BucketIndex = 0; BucketIndex < Table->Count; ++BucketIndex)
  {
    Table->Elements[BucketIndex] = 0;
  }
}

void MarkSweepHeap::Init(int collection_thresh) {
  this->collection_thresh_ = collection_thresh;

#if 0
  this->all_allocations_.reserve(10 * MiB(1));

  auto all = this->all_allocations_;
  log("bucket_count %d", all.bucket_count());
  log("max_bucket_count %u", all.max_bucket_count());

  this->marked_allocations_.reserve(MiB(1));
#else

  AllocateHashtable(&this->marked_allocations_, KiB(1));
  AllocateHashtable(&this->all_allocations_, KiB(1000));

#endif
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

  HashtableInsert(&this->all_allocations_, result);

  /* if (this->num_live_objs_ % 100000 == 0) { */
  /*   auto all = this->all_allocations_; */
  /*   log("live %d", this->num_live_objs_); */
  /*   log("bucket_count %d", all.bucket_count()); */
  /*   log("load_factor %f", all.load_factor()); */
  /*   log("max_load_factor %f", all.max_load_factor()); */
  /* } */

  return result;
}

void MarkSweepHeap::MarkAllReferences(Obj* obj) {
  auto header = ObjHeader(obj);

  if (HashtableContains(&marked_allocations_, obj))
  {
    return;
  }

  HashtableInsert(&this->marked_allocations_, (void*)obj);

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

#if 0
  for (auto it = all_allocations_.Count(); it != all_allocations_.end(); ++it) {
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
#else
  for (umm BucketIndex = 0; BucketIndex < all_allocations_.Count; ++BucketIndex)
  {
    void *alloc = all_allocations_.Elements[BucketIndex];
    if (alloc)
    {
      if (!HashtableContains(&marked_allocations_, alloc))
      {
        free(alloc);
#if GC_STATS
        this->num_live_objs_--;
#endif
      }
      else
      {
        /* int breakhere = 0; */
      }
    }
  }
#endif

  HashtableClear(&all_allocations_);
  int objectsInserted = 0;
  for (umm BucketIndex = 0; BucketIndex < marked_allocations_.Count; ++BucketIndex)
  {
    Obj *obj = (Obj*)marked_allocations_.Elements[BucketIndex];
    if (obj && ObjHeader(obj)->heap_tag_ != Tag::Global) {
      ++objectsInserted;
      HashtableInsert(&all_allocations_, (void*)obj);
    }
  }

#if GC_STATS
  // TODO(Jesse): This assertion fails but all the tests pass!  Is this a
  // pre-existing bug or one with this hashtable impl?  I'm guessing it's
  // been lurking..
  //
  // assert(this->num_live_objs_ == objectsInserted);
#endif

#if 0
  for (auto it = marked_allocations_.begin(); it != marked_allocations_.end(); ++it) {
    Obj* obj = reinterpret_cast<Obj*>(*it);
    if (obj->heap_tag_ != Tag::Global) {
      all_allocations_.insert(*it);
    }
  }
#endif

  HashtableClear(&marked_allocations_);
}

#if MARK_SWEEP
MarkSweepHeap gHeap;
#endif
