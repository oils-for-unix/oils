#ifndef GC_SLAB_H
#define GC_SLAB_H

// Return the size of a resizeable allocation.  For now we just round up by
// powers of 2. This could be optimized later.  CPython has an interesting
// policy in listobject.c.
//
// https://stackoverflow.com/questions/466204/rounding-up-to-next-power-of-2
inline int RoundUp(int n) {
  // minimum size
  if (n < 8) {
    return 8;
  }

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

// Opaque slab, e.g. for List<int>
template <typename T>
class Slab {
 public:
  // slabs of pointers are scanned; slabs of ints/bools are opaque.
  explicit Slab(uint32_t obj_len)
      : GC_SLAB(header_,
                std::is_pointer<T>() ? HeapTag::Scanned : HeapTag::Opaque,
                obj_len) {
  }
  GC_OBJ(header_);
  T items_[1];  // variable length

  DISALLOW_COPY_AND_ASSIGN(Slab);
};

template <typename T, int N>
class GlobalSlab {
  // A template type with the same layout as Str with length N-1 (which needs a
  // buffer of size N).  For initializing global constant instances.
 public:
  ObjHeader header_;
  T items_[N];

  DISALLOW_COPY_AND_ASSIGN(GlobalSlab)
};

// The first field is items_
const int kSlabHeaderSize = offsetof(Slab<int>, items_);

// Note: entries will be zero'd because the Heap is zero'd.
template <typename T>
inline Slab<T>* NewSlab(int len) {
  int obj_len = RoundUp(kSlabHeaderSize + len * sizeof(T));
  void* place = gHeap.Allocate(obj_len);
  auto slab = new (place) Slab<T>(obj_len);  // placement new
  return slab;
}

#endif  // GC_SLAB_H
