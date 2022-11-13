#include "cpp/osh.h"
#include "cpp/core_error.h"
#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST bool_stat_test() {
  int fail = 0;
  try {
    bool_stat::isatty(StrFromC("invalid"), nullptr);
  } catch (error::FatalRuntime* e) {
    fail++;
  }
  ASSERT_EQ(1, fail);

  bool b2 = bool_stat::isatty(StrFromC("0"), nullptr);
  // This will be true interactively
  log("stdin isatty = %d", b2);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(bool_stat_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
