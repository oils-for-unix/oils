#include "cpp/qsn.h"

#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST qsn_test() {
  Str* x = qsn::XEscape(StrFromC("a"));
  log("XEscape %s", x->data_);
  ASSERT(str_equals(x, StrFromC("\\x61")));

  Str* u = qsn::UEscape(0x61);
  log("UEScape %s", u->data_);
  ASSERT(str_equals(u, StrFromC("\\u{61}")));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  // Can stress test it like this
  for (int i = 0; i < 10; ++i) {
    RUN_TEST(qsn_test);
  }

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
