#ifndef GC_ALLOC_H
#define GC_ALLOC_H

// Variadic templates:
// https://eli.thegreenplace.net/2014/variadic-templates-in-c/
template <typename T, typename... Args>
T* Alloc(Args&&... args) {
  assert(gHeap.is_initialized_);

  void* place = gHeap.Allocate(sizeof(T));
  assert(place != nullptr);
  // placement new
  return new (place) T(std::forward<Args>(args)...);
}

#endif  // GC_ALLOC_H
