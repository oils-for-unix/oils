#include <assert.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>   // vprintf

#include "gc_heap.h"
#include "greatest.h"
#include "my_runtime.h"

using gc_heap::gHeap;

GLOBAL_STR(kString1, "food");
GLOBAL_STR(kWithNull, "foo\0bar");

TEST print_test() {
  print(kString1);
  println_stderr(kString1);

  print(kWithNull);
  println_stderr(kWithNull);

  PASS();
}

TEST str_replace_test() {
  Str* s = kString1->replace(NewStr("o"), NewStr("12"));
  ASSERT(str_equals(NewStr("f1212d"), s));
  print(s);

  // BUG in corner case!
  Str* s2 = NewStr("foo")->replace(NewStr("o"), NewStr("123"));
  ASSERT(str_equals(NewStr("f123123"), s2));
  print(s2);

  Str* s3 = NewStr("foxo")->replace(NewStr("o"), NewStr("123"));
  ASSERT(str_equals(NewStr("f123x123"), s3));
  print(s3);

  Str* s4 = kWithNull->replace(NewStr("a"), NewStr("XX"));
  print(s4);
  // Explicit length because of \0
  ASSERT(str_equals(NewStr("foo\0bXXr", 8), s4));

  PASS();
}

TEST formatter_test() {
  gBuf.reset();
  gBuf.write_const("[", 1);
  gBuf.format_s(NewStr("bar"));
  gBuf.write_const("]", 1);
  log("value = %s", gBuf.getvalue()->data_);

  gBuf.format_d(42);
  gBuf.write_const("-", 1);
  gBuf.format_d(42);
  gBuf.write_const(".", 1);
  log("value = %s", gBuf.getvalue()->data_);

  PASS();
}

GLOBAL_STR(b, "b");
GLOBAL_STR(bb, "bx");

TEST collect_test() {
  gHeap.Init(1 << 8);  // 1 KiB

  auto s = NewStr("abcdefg");
  for (int i = 0; i < 40; ++i) {
    s = s->replace(b, bb);

    Str* t = NewStr("NUL");

    // log("i = %d", i);
    // log("len(s) = %d", len(s));
  }

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(print_test);
  RUN_TEST(str_replace_test);
  RUN_TEST(formatter_test);
  RUN_TEST(collect_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
