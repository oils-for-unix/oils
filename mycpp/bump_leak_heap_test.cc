#include "mycpp/bump_leak_heap.h"

#include <unistd.h>  // STDERR_FILENO

#include "mycpp/gc_alloc.h"  // gHeap
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

// Test empty and trivial methods
TEST for_code_coverage() {
  BumpLeakHeap h;

  h.Init();
  h.Init(10);
  h.PushRoot(nullptr);
  h.PopRoot();
  h.RootGlobalVar(nullptr);
  (void)h.Allocate(10);
  ASSERT_EQ(-1, h.MaybeCollect());

  h.PrintStats(STDERR_FILENO);

  h.FastProcessExit();
  h.CleanProcessExit();

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(Reallocate_test);
  RUN_TEST(for_code_coverage);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
