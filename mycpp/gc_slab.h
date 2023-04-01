#ifndef GC_SLAB_H
#define GC_SLAB_H

#include <utility>  // std::is_pointer

#include "mycpp/common.h"  // DISALLOW_COPY_AND_ASSIGN
#include "mycpp/gc_obj.h"

// Return the size of a resizeable allocation.  Just round up to the nearest
// power of 2.  (CPython has an interesting policy in listobject.c.)
//
// https://stackoverflow.com/questions/466204/rounding-up-to-next-power-of-2
//
// Used by List<T> and Dict<K, V>.

inline int RoundUp(int n) {
  // TODO: what if int isn't 32 bits?
  n--;
  n |= n >> 1;
  n |= n >> 2;
  n |= n >> 4;
  n |= n >> 8;
  n |= n >> 16;
  n++;
  return n;
}

template <typename T>
class Slab {
  // Slabs of pointers are scanned; slabs of ints/bools are opaque.
 public:
  explicit Slab(unsigned num_items) {
  }

  static constexpr ObjHeader obj_header(unsigned num_items) {
    return ObjHeader::Slab(
        std::is_pointer<T>() ? HeapTag::Scanned : HeapTag::Opaque, num_items);
  }

  T items_[1];  // variable length

  DISALLOW_COPY_AND_ASSIGN(Slab);
};

template <typename T, int N>
class GlobalSlab {
  // A template type with the same layout as Slab of length N.  For
  // initializing global constant List.
 public:
  T items_[N];

  DISALLOW_COPY_AND_ASSIGN(GlobalSlab)
};

// XXX(watk): Does this make sense?
const int kSlabHeaderSize = sizeof(ObjHeader);

#endif  // GC_SLAB_H
