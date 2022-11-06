#include "mycpp/runtime.h"
#include "vendor/greatest.h"

BumpLeakHeap gBumpLeakHeap;

TEST Reallocate_test() {
  log("sizeof(size_t) = %zu", sizeof(size_t));

  char* p1 = static_cast<char*>(gBumpLeakHeap.Allocate(10));
  strcpy(p1, "abcdef");

  char* p2 = static_cast<char*>(gBumpLeakHeap.Reallocate(p2, 20));
  // ASSERT_EQ(0, strcmp(p1, p2));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(Reallocate_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
