#include "mycpp/cheney_heap.h"

#include "vendor/greatest.h"

// TODO: gc_heap_test.cc used to run with the cheney_heap.h.  Maybe revive
// that.

TEST header_test() {
  CheneyHeap h;

  h.Init(100);
  h.Collect(200);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  // gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(header_test);

  // gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
