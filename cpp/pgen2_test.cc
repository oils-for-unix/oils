#include "cpp/pgen2.h"

#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST allocator_test() {
  for (int i = 0; i < 6000; i += 100) {
    pnode::PNodeAllocator p;
    log("Testing i = %d\n", i);
    for (int j = 0; j < i; ++j) {
      p.NewPNode(1, nullptr);
    }
    // TODO: it woudl be nicer to reuse the std::deque
    p.Clear();
  }
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
