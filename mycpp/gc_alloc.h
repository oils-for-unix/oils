#ifndef GC_ALLOC_H
#define GC_ALLOC_H

/* class Heap; */
/* extern Heap gHeap; */

// Variadic templates:
// https://eli.thegreenplace.net/2014/variadic-templates-in-c/
template <typename T, typename... Args>
T* Alloc(Args&&... args) {
  void* place = gHeap.Allocate(sizeof(T));
  assert(place != nullptr);
  // placement new
  return new (place) T(std::forward<Args>(args)...);
}

#endif  // GC_ALLOC_H
