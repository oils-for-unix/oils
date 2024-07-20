// For unit tests only

#ifndef TEST_COMMON_H
#define TEST_COMMON_H

#include "mycpp/gc_obj.h"

class Point {
 public:
  Point(int x, int y) : x_(x), y_(y) {
  }
  int size() {
    return x_ + y_;
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(kZeroMask, sizeof(Point));
  }

  int x_;
  int y_;
};

#endif  // TEST_COMMON_H
