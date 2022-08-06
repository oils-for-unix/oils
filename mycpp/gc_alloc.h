#ifndef GC_ALLOC_H
#define GC_ALLOC_H

/* class Heap; */
/* extern Heap gHeap; */

#ifdef MYLIB_LEAKY

#define ALLOCATE(byte_count) calloc(byte_count, 1)

#else
  using gc_heap::Heap;
  using gc_heap::gHeap;
#define ALLOCATE(byte_count) gHeap.Allocate(byte_count)
#endif

// Variadic templates:
// https://eli.thegreenplace.net/2014/variadic-templates-in-c/
template <typename T, typename... Args>
T* Alloc(Args&&... args) {
  void* place = ALLOCATE(sizeof(T)); 
  assert(place != nullptr);
  // placement new
  return new (place) T(std::forward<Args>(args)...);
}

#endif  // GC_ALLOC_H
