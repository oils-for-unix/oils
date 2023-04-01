#include "mycpp/cheney_heap.h"

#include <sys/mman.h>  // mmap

#include "mycpp/gc_obj.h"
#include "mycpp/gc_slab.h"

#ifdef CHENEY_GC

CheneyHeap gHeap;

class LayoutForwarded {
 public:
  ObjHeader header_;
  // valid if and only if heap_tag == HeapTag::Forwarded
  RawObject* new_location;
};

void Space::Init(int num_bytes) {
  void* requested_addr = nullptr;

  int fd = -1;  // `man 2 mmap` notes that a portable application should set
                // the fd argument to -1 with MAP_ANONYMOUS because some impls
                // require it.

  int offset = 0;  // `man 2 mmap` specifies this must be 0 with MAP_ANONYMOUS

  void* p = mmap(requested_addr, num_bytes, PROT_READ | PROT_WRITE,
                 MAP_PRIVATE | MAP_ANONYMOUS, fd, offset);

  if (p == MAP_FAILED) {
    assert(!"mmap() failed, infinite sadness.");
  } else {
    begin_ = static_cast<char*>(p);
    size_ = num_bytes;
  }
}

void Space::Free() {
  munmap(begin_, size_);
}

RawObject* CheneyHeap::Relocate(RawObject* obj, ObjHeader* header) {
  // Move an object from one space to another.
  // If there's no vtable, then obj == header.  Otherwise header points to the
  // RawObject header, which is right after the vtable.

  switch (header->heap_tag) {
  case HeapTag::Forwarded: {
    auto f = reinterpret_cast<LayoutForwarded*>(header);
    return f->new_location;
  }

  case HeapTag::Global: {  // e.g. GlobalStr isn't copied or forwarded
    // log("*** GLOBAL POINTER");
    return obj;
  }

  default: {
    assert(header->heap_tag == HeapTag::Opaque ||
           header->heap_tag == HeapTag::FixedSize ||
           header->heap_tag == HeapTag::Scanned);

    auto new_location = reinterpret_cast<RawObject*>(free_);
    // Note: if we wanted to save space on ASDL records, we could calculate
    // their length from the field_mask here.  How much would it slow down GC?
    int n = header->obj_len;
    assert(n > 0);  // detect common problem
    memcpy(new_location, obj, n);
    // log("memcpy %d bytes from %p -> %p", n, obj, new_location);
  #if 0
    if (obj->heap_tag == HeapTag::Opaque) {
      Str* s = static_cast<Str*>(obj);
      log("from = %s", s->data_);
      Str* s2 = static_cast<Str*>(new_location);
      log("to = %s", s2->data_);
    }
  #endif
    // aligned() like Heap::Allocate()
    free_ += aligned(n);

  #if GC_STATS
    num_live_objs_++;
  #endif

    auto f = reinterpret_cast<LayoutForwarded*>(header);
    f->header_.heap_tag = HeapTag::Forwarded;
    f->new_location = new_location;
    return new_location;
  }
  }  // switch
}

void CheneyHeap::Collect(int to_space_size) {
  #if GC_STATS
  log("--> COLLECT with %d roots", roots_top_);
  num_collections_++;
  #endif

  if (to_space_size == 0) {
    to_space_size = from_space_.size_;
  }

  assert(to_space_size >= from_space_.size_);

  to_space_.Init(to_space_size);

  assert(to_space_.size_ >= from_space_.size_);

  char* scan = to_space_.begin_;  // boundary between black and gray
  free_ = scan;                   // where to copy new entries
  limit_ = scan + to_space_.size_;

  #if GC_STATS
  num_live_objs_ = 0;
  #endif

  for (int i = 0; i < roots_top_; ++i) {
    RawObject** handle = roots_[i];
    auto root = *handle;
  #if GC_VERBOSE
    log("%d. handle %p", i, handle);
    log("    root %p", root);
  #endif

    if (root) {  // could be nullptr
      auto header = ObjHeader::FromObject(root);

      // This updates the underlying Str/List/Dict with a forwarding pointer,
      // i.e. for other objects that are pointing to it
      RawObject* new_location = Relocate(root, header);
  #if TODO_BUG
      for (int j = 0; j < roots_top_; ++j) {
        RawObject** handle2 = roots_[j];
        auto root2 = *handle2;
        if (root2) {
          switch (root2->heap_tag) {
          case HeapTag::Forwarded:
          case HeapTag::Global:
          case HeapTag::Opaque:
          case HeapTag::FixedSize:
          case HeapTag::Scanned:
            break;
          default:
            FAIL(kShouldNotGetHere);
          }
        }
      }

  #endif

      // log("    new location %p", new_location);

      // This update is for the "double indirection", so future accesses to a
      // local variable use the new location
      *handle = new_location;
    }
  }

  while (scan < free_) {
    auto obj = reinterpret_cast<RawObject*>(scan);
    auto header = ObjHeader::FromObject(obj);

    switch (header->heap_tag) {
    case HeapTag::FixedSize: {
      auto fixed = reinterpret_cast<LayoutFixed*>(obj);
      int mask = ObjHeader::FromObject(obj)->field_mask;
      for (int i = 0; i < 16; ++i) {
        if (mask & (1 << i)) {
          RawObject* child = fixed->children_[i];
          // log("i = %d, p = %p, heap_tag = %d", i, child, child->heap_tag);
          if (child) {
            auto child_header = ObjHeader::FromObject(child);
            // log("  fixed: child %d from %p", i, child);
            fixed->children_[i] = Relocate(child, child_header);
            // log("  to %p", fixed->children_[i]);
          }
        }
      }
      break;
    }
    case HeapTag::Scanned: {
      auto slab = reinterpret_cast<Slab<void*>*>(obj);
      auto header = ObjHeader::FromObject(obj);
      int n = (header->obj_len - kSlabHeaderSize) / sizeof(void*);
      for (int i = 0; i < n; ++i) {
        RawObject* child = reinterpret_cast<RawObject*>(slab->items_[i]);
        if (child) {  // note: List<> may have nullptr; Dict is sparse
          auto child_header = ObjHeader::FromObject(child);
          slab->items_[i] = Relocate(child, child_header);
        }
      }
      break;
    }
    default: {
      assert(header->heap_tag == HeapTag::Forwarded ||
             header->heap_tag == HeapTag::Global ||
             header->heap_tag == HeapTag::Opaque);
    }

      // other tags like HeapTag::Opaque have no children
    }
    // aligned() like Heap::Allocate()
    scan += aligned(header->obj_len);
  }

  Swap();

  to_space_.Free();

  #if GC_STATS
  Report();
  #endif
}

  #if GC_STATS
void ShowFixedChildren(RawObject* obj) {
  assert(obj->heap_tag == HeapTag::FixedSize);
  auto fixed = reinterpret_cast<LayoutFixed*>(obj);
  log("MASK:");

  // Note: can this be optimized with the equivalent x & (x-1) trick?
  // We need the index
  // There is a de Brjuin sequence solution?
  // https://stackoverflow.com/questions/757059/position-of-least-significant-bit-that-is-set

  int mask = fixed->field_mask;
  for (int i = 0; i < 16; ++i) {
    if (mask & (1 << i)) {
      RawObject* child = fixed->children_[i];
      if (child) {
        // make sure we get HeapTag::Opaque, HeapTag::Scanned, etc.
        log("i = %d, p = %p, heap_tag = %d", i, child, child->heap_tag);
      }
    }
  }
}
  #endif

void* CheneyHeap::Allocate(int num_bytes) {
  int n = aligned(num_bytes);
  // log("n = %d, p = %p", n, p);

  // This must be at least sizeof(LayoutForwarded), which happens to be 16
  // bytes, because the GC pointer forwarding requires 16 bytes.  If we
  // allocated less than 16 the GC would overwrite the adjacent object when
  // it went to forward the pointer.
  assert(n >= static_cast<int>(sizeof(LayoutForwarded)));

  #if GC_ALWAYS
  Collect();  // force collection to find problems early
  #endif

  if (free_ + n <= limit_) {  // Common case: we have space for it.
    return Bump(n);
  }

  #if GC_STATS
    // log("GC free_ %p,  from_space_ %p, space_size_ %d", free_, from_space_,
    //    space_size_);
  #endif

  Collect();  // Try to free some space.

  // log("after GC: from begin %p, free_ %p,  n %d, limit_ %p",
  //    from_space_.begin_, free_, n, limit_);

  if (free_ + n <= limit_) {  // Now we have space for it.
    return Bump(n);
  }

  // It's still too small.  Grow the heap.
  int multiple = 2;
  Collect((from_space_.size_ + n) * multiple);

  #if GC_STATS
  num_forced_growths_++;
  #endif

  return Bump(n);
}

#endif  // CHENEY_GC
