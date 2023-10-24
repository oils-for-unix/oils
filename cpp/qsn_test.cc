#include "cpp/qsn.h"

#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST qsn_test() {
  BigStr* x = qsn::XEscape(StrFromC("a"));
  log("XEscape %s", x->data_);
  ASSERT(str_equals(x, StrFromC("\\x61")));

  BigStr* u = qsn::UEscape(0x61);
  log("UEScape %s", u->data_);
  ASSERT(str_equals(u, StrFromC("\\u{61}")));

  ASSERT(qsn::IsUnprintableLow(StrFromC("\x01")));
  ASSERT(!qsn::IsUnprintableLow(StrFromC(" ")));
  ASSERT(!qsn::IsUnprintableLow(StrFromC("\xce")));
  ASSERT(!qsn::IsUnprintableLow(StrFromC("\xbc")));

  ASSERT(qsn::IsUnprintableHigh(StrFromC("\xff")));
  ASSERT(!qsn::IsUnprintableHigh(StrFromC("\x01")));

  ASSERT(qsn::IsPlainChar(StrFromC("a")));
  ASSERT(qsn::IsPlainChar(StrFromC("-")));
  ASSERT(!qsn::IsPlainChar(StrFromC(" ")));

  // UTF-8 bytes for mu
  ASSERT(!qsn::IsPlainChar(StrFromC("\xce")));
  ASSERT(!qsn::IsPlainChar(StrFromC("\xbc")));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(qsn_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
