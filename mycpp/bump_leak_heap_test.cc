#include "mycpp/runtime.h"
#include "vendor/greatest.h"

BumpLeakHeap gBumpLeakHeap;

TEST bump_leak_heap_test() {
  char* p1 = static_cast<char*>(gBumpLeakHeap.Allocate(10));
  strcpy(p1, "abcdef");

  char* p2 = static_cast<char*>(gBumpLeakHeap.Reallocate(p2, 20));
  // TODO: Make this pass
  // ASSERT_EQ(0, strcmp(p1, p2));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(bump_leak_heap_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
