#include "cpp/qsn.h"
#include "vendor/greatest.h"

// This test runs primarily in the GC mode, but you can also run it in the
// leaky mode!


#ifdef OLDSTL_BINDINGS
  #include "mycpp/oldstl_containers.h"
#else
  #include "mycpp/gc_containers.h"
#endif

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
  gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  // Can stress test it like this
  for (int i = 0; i < 10; ++i) {
    RUN_TEST(qsn_test);
  }

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
