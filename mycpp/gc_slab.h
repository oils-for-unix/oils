#ifndef GC_SLAB_H
#define GC_SLAB_H

template <typename T>
inline void InitSlabCell(Obj* obj) {
  // log("SCANNED");
  obj->heap_tag_ = Tag::Scanned;
}

template <>
inline void InitSlabCell<int>(Obj* obj) {
  // log("OPAQUE");
  obj->heap_tag_ = Tag::Opaque;
}

// don't include items_[1]
const int kSlabHeaderSize = sizeof(Obj);

// Opaque slab, e.g. for List<int>
template <typename T>
class Slab : public Obj {
 public:
  Slab(int obj_len) : Obj(0, 0, obj_len) {
    InitSlabCell<T>(this);
  }
  T items_[1];  // variable length
};

template <typename T, int N>
class GlobalSlab {
  // A template type with the same layout as Str with length N-1 (which needs a
  // buffer of size N).  For initializing global constant instances.
 public:
  OBJ_HEADER()

  T items_[N];

  DISALLOW_COPY_AND_ASSIGN(GlobalSlab)
};

// Note: entries will be zero'd because the Heap is zero'd.
template <typename T>
inline Slab<T>* NewSlab(int len) {
  int obj_len = RoundUp(kSlabHeaderSize + len * sizeof(T));
  void* place = gHeap.Allocate(obj_len);
  auto slab = new (place) Slab<T>(obj_len);  // placement new
  return slab;
}


#endif  // GC_SLAB_H
