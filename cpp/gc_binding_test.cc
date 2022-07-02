#include "cpp/qsn_qsn.h"
#include "vendor/greatest.h"

// This test runs primarily in the GC mode, but you can also run it in the
// leaky mode!

#ifdef LEAKY_TEST_MODE
#include "mycpp/gc_heap.h"
#include "mycpp/mylib.h"
using gc_heap::StackRoots;  // no-op
using mylib::CopyStr;
#else
#include "mycpp/gc_heap.h"
using gc_heap::CopyStr;
using gc_heap::StackRoots;
#endif

TEST qsn_test() {
  Str* s = nullptr;
  Str* x = nullptr;
  Str* u = nullptr;
  StackRoots _roots({&s, &x, &u});

  s = CopyStr("a");
  x = qsn::XEscape(s);
  log("XEscape %s", x->data_);
  ASSERT(str_equals(x, CopyStr("\\x61")));

  u = qsn::UEscape(0x61);
  log("UEScape %s", u->data_);
  ASSERT(str_equals(u, CopyStr("\\u{61}")));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gc_heap::gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  // Can stress test it like this
  for (int i = 0; i < 10; ++i) {
    RUN_TEST(qsn_test);
  }

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
