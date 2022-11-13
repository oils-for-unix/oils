#include "cpp/qsn.h"

#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST qsn_test() {
  Str* s = nullptr;
  Str* x = nullptr;
  Str* u = nullptr;
  StackRoots _roots({&s, &x, &u});

  s = StrFromC("a");
  x = qsn::XEscape(s);
  log("XEscape %s", x->data_);
  ASSERT(str_equals(x, StrFromC("\\x61")));

  u = qsn::UEscape(0x61);
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
