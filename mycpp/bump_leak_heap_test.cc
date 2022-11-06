#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST Reallocate_test() {
  log("sizeof(size_t) = %zu", sizeof(size_t));

  BumpLeakHeap h;

  char* p1 = static_cast<char*>(h.Allocate(10));
  strcpy(p1, "abcdef");
  log("p1 = %p %s", p1, p1);

  char* p2 = static_cast<char*>(h.Reallocate(p1, 20));
  log("p2 = %p %s", p2, p2);
  ASSERT_EQ_FMT(0, strcmp(p1, p2), "%d");

  char* p3 = static_cast<char*>(h.Reallocate(p2, 30));
  log("p3 = %p %s", p3, p3);
  ASSERT_EQ_FMT(0, strcmp(p1, p3), "%d");

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(Reallocate_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
