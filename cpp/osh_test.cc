#include "cpp/osh.h"

#include "mycpp/runtime.h"
// To avoid circular dependency with error.FatalRuntime
#include "prebuilt/core/error.mycpp.h"
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

TEST functions_test() {
  ASSERT(sh_expr_eval::IsLower(StrFromC("a")));
  ASSERT(!sh_expr_eval::IsLower(StrFromC("A")));
  ASSERT(!sh_expr_eval::IsLower(StrFromC("9")));

  ASSERT(sh_expr_eval::IsUpper(StrFromC("Z")));
  ASSERT(!sh_expr_eval::IsUpper(StrFromC("z")));
  ASSERT(!sh_expr_eval::IsUpper(StrFromC("9")));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(bool_stat_test);
  RUN_TEST(functions_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
