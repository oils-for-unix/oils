#ifndef MARKSWEEP_H
#define MARKSWEEP_H

#include <new>

#define Terabytes(bytes) (Gigabytes(bytes)*1024)
#define Gigabytes(bytes) (Megabytes(bytes)*1024)
#define Megabytes(bytes) (Kilobytes(bytes)*1024)
#define Kilobytes(bytes) ((bytes)*1024)


const int kMaxRoots = Kilobytes(4);

class Heap {
 public:
  Heap() {}

  void Init(int space_size) {}

  void *Allocate(int);

  void PushRoot(Obj** p) {
    assert(roots_top_ < kMaxRoots);
    roots_[roots_top_++] = p;
  }

  void PopRoot() {
    roots_top_--;
  }

  void Collect(int to_space_size = 0);

  int roots_top_;
  Obj** roots_[kMaxRoots];  // These are pointers to Obj* pointers

  bool is_initialized_ = false;

};

#endif

