#include "cpp/pgen2.h"

#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST allocator_test() {
  pnode::PNodeAllocator p;
  for (int i = 0; i < 1000; ++i) {
    p.NewPNode(1, nullptr);
  }
  p.Clear();

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(allocator_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
