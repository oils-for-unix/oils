// gc_heap.cc

#include "gc_heap.h"

#include <sys/mman.h>  // mprotect()

using gc_heap::Heap;
using gc_heap::Local;
using gc_heap::Obj;

namespace gc_heap {

GLOBAL_STR(kEmptyString, "");

Heap gHeap;

// LayoutForwarded and LayoutFixed aren't real types.  You can cast arbitrary
// objs to them to access a HOMOGENEOUS REPRESENTATION useful for garbage
// collection.

class LayoutForwarded : public Obj {
 public:
  Obj* new_location;  // valid if and only if heap_tag_ == Tag::Forwarded
};

// for Tag::FixedSize
class LayoutFixed : public Obj {
 public:
  Obj* children_[16];  // only the entries denoted in field_mask will be valid
};

void Space::Init(int space_size) {
#if GC_PROTECT
  void* p = mmap(nullptr, space_size, PROT_READ | PROT_WRITE,
                 MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  begin_ = static_cast<char*>(p);
#else
  begin_ = static_cast<char*>(malloc(space_size));
#endif
  size_ = space_size;
  Clear();
}

void Space::Free() {
#if GC_PROTECT
  Protect();  // There is no way of deallocating I guess
#else
  free(begin_);
#endif
}

#if GC_PROTECT
void Space::Protect() {
  int m = mprotect(begin_, size_, PROT_NONE);
  assert(m == 0);
}

void Space::Unprotect() {
  int m = mprotect(begin_, size_, PROT_READ | PROT_WRITE);
  assert(m == 0);
}
#endif

Obj* Heap::Relocate(Obj* obj, Obj* header) {
  // Move an object from one space to another.
  // If there's no vtable, then obj == header.  Otherwise header points to the
  // Obj header, which is right after the vtable.

  switch (header->heap_tag_) {
  case Tag::Forwarded: {
    auto f = reinterpret_cast<LayoutForwarded*>(header);
    return f->new_location;
  }

  case Tag::Global: {  // e.g. GlobalStr isn't copied or forwarded
    // log("*** GLOBAL POINTER");
    return obj;
  }

  default: {
    assert(header->heap_tag_ == Tag::Opaque ||
           header->heap_tag_ == Tag::FixedSize ||
           header->heap_tag_ == Tag::Scanned);

    auto new_location = reinterpret_cast<Obj*>(free_);
    // Note: if we wanted to save space on ASDL records, we could calculate
    // their length from the field_mask here.  How much would it slow down GC?
    int n = header->obj_len_;
    assert(n > 0);  // detect common problem
    memcpy(new_location, obj, n);
    // log("memcpy %d bytes from %p -> %p", n, obj, new_location);
#if 0
    if (obj->heap_tag_ == Tag::Opaque) {
      Str* s = static_cast<Str*>(obj);
      log("from = %s", s->data_);
      Str* s2 = static_cast<Str*>(new_location);
      log("to = %s", s2->data_);
    }
#endif
    free_ += n;

#if GC_DEBUG
    num_live_objs_++;
#endif

    auto f = reinterpret_cast<LayoutForwarded*>(header);
    f->heap_tag_ = Tag::Forwarded;
    f->new_location = new_location;
    return new_location;
  }
  }  // switch
}

inline Obj* ObjHeader(Obj* obj) {
  // If we see a vtable pointer, return the Obj* header immediately following.
  // Otherwise just return Obj itself.
  return (obj->heap_tag_ & 0x1) == 0
             ? reinterpret_cast<Obj*>(reinterpret_cast<char*>(obj) +
                                      sizeof(void*))
             : obj;
}

void Heap::Collect() {
#if GC_DEBUG
  log("--> COLLECT with %d roots", roots_top_);
  num_collections_++;
#endif

#if GC_PROTECT
  to_space_.Unprotect();
#endif

  // If we grew one space, the other one has to catch up.
  if (to_space_.size_ < from_space_.size_) {
    to_space_.Free();
    to_space_.Init(from_space_.size_);
  }

  char* scan = to_space_.begin_;  // boundary between black and gray
  free_ = scan;                   // where to copy new entries
  limit_ = scan + to_space_.size_;

#if GC_DEBUG
  num_live_objs_ = 0;
#endif

  for (int i = 0; i < roots_top_; ++i) {
    Obj** handle = roots_[i];
    auto root = *handle;
#if GC_VERBOSE
    log("%d. handle %p", i, handle);
    log("    root %p", root);
#endif

    if (root) {  // could be nullptr
      auto header = ObjHeader(root);

      // This updates the underlying Str/List/Dict with a forwarding pointer,
      // i.e. for other objects that are pointing to it
      Obj* new_location = Relocate(root, header);
#if TODO_BUG
      for (int j = 0; j < roots_top_; ++j) {
        Obj** handle2 = roots_[j];
        auto root2 = *handle2;
        if (root2) {
          switch (root2->heap_tag_) {
            case Tag::Forwarded:
            case Tag::Global:
            case Tag::Opaque:
            case Tag::FixedSize:
            case Tag::Scanned:
              break;
            default:
              assert(0);
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
    auto obj = reinterpret_cast<Obj*>(scan);
    auto header = ObjHeader(obj);

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
            fixed->children_[i] = Relocate(child, child_header);
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
          slab->items_[i] = Relocate(child, child_header);
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
    scan += header->obj_len_;
  }

  // We just copied everything from_space_ -> to_space_.  Maintain
  // invariant of the space we will allocate from next time.
  from_space_.Clear();
#if GC_PROTECT
  from_space_.Protect();
  // log("begin = %x", *from_space_.begin_);
#endif

  Swap();

#if GC_VERBOSE
  Report();
#endif
}

bool str_equals(Str* left, Str* right) {
  // Fast path for identical strings.  String deduplication during GC could
  // make this more likely.  String interning could guarantee it, allowing us
  // to remove memcmp().
  if (left == right) {
    return true;
  }
  // obj_len_ equal implies string lengths are equal
  if (left->obj_len_ == right->obj_len_) {
    return memcmp(left->data_, right->data_, len(left)) == 0;
  }
  return false;
}

bool maybe_str_equals(Str* left, Str* right) {
  if (left && right) {
    return str_equals(left, right);
  }

  if (!left && !right) {
    return true;  // None == None
  }

  return false;  // one is None and one is a Str*
}

#if GC_DEBUG
void ShowFixedChildren(Obj* obj) {
  assert(obj->heap_tag_ == Tag::FixedSize);
  auto fixed = reinterpret_cast<LayoutFixed*>(obj);
  log("MASK:");

  // Note: can this be optimized with the equivalent x & (x-1) trick?
  // We need the index
  // There is a de Brjuin sequence solution?
  // https://stackoverflow.com/questions/757059/position-of-least-significant-bit-that-is-set

  int mask = fixed->field_mask_;
  for (int i = 0; i < 16; ++i) {
    if (mask & (1 << i)) {
      Obj* child = fixed->children_[i];
      if (child) {
        // make sure we get Tag::Opaque, Tag::Scanned, etc.
        log("i = %d, p = %p, heap_tag = %d", i, child, child->heap_tag_);
      }
    }
  }
}
#endif

}  // namespace gc_heap
