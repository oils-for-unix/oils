#ifndef LEAKY_HEAP_H
#define LEAKY_HEAP_H

class Obj;

struct Heap {
  void Init(int byte_count) {
  }

  void Bump() {
  }

  void Collect() {
  }

  void* Allocate(int num_bytes) {
    return calloc(num_bytes, 1);
  }

  void PushRoot(Obj** p) {
  }

  void PopRoot() {
  }
};

extern Heap gHeap;

struct StackRoots {
  StackRoots(std::initializer_list<void*> roots) {
  }
};

#endif
