#ifdef OLDSTL_BINDINGS
  // clang-format off
  #include "mycpp/oldstl_containers.h"
  #include "mycpp/oldstl_builtins.h"
// clang-format on
#else
  #include "mycpp/gc_builtins.h"
  #include "mycpp/gc_containers.h"
#endif

#include "vendor/greatest.h"

GLOBAL_STR(kSpace, " ");

TEST test_str_to_int() {
  int i;
  bool ok;

  ok = _str_to_int(StrFromC("345"), &i, 10);
  ASSERT(ok);
  ASSERT_EQ_FMT(345, i, "%d");

  ok = _str_to_int(StrFromC("1234567890"), &i, 10);
  ASSERT(ok);
  ASSERT(i == 1234567890);

  // overflow
  ok = _str_to_int(StrFromC("12345678901234567890"), &i, 10);
  ASSERT(!ok);

  // underflow
  ok = _str_to_int(StrFromC("-12345678901234567890"), &i, 10);
  ASSERT(!ok);

  // negative
  ok = _str_to_int(StrFromC("-123"), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Leading space is OK!
  ok = _str_to_int(StrFromC(" -123"), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Trailing space is OK!  NOTE: This fails!
  ok = _str_to_int(StrFromC(" -123  "), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Empty string isn't an integer
  ok = _str_to_int(StrFromC(""), &i, 10);
  ASSERT(!ok);

  ok = _str_to_int(StrFromC("xx"), &i, 10);
  ASSERT(!ok);

  // Trailing garbage
  ok = _str_to_int(StrFromC("42a"), &i, 10);
  ASSERT(!ok);

  i = to_int(StrFromC("ff"), 16);
  ASSERT(i == 255);

  // strtol allows 0x prefix
  i = to_int(StrFromC("0xff"), 16);
  ASSERT(i == 255);

  // TODO: test ValueError here
  // i = to_int(StrFromC("0xz"), 16);

  i = to_int(StrFromC("0"), 16);
  ASSERT(i == 0);

  i = to_int(StrFromC("077"), 8);
  ASSERT_EQ_FMT(63, i, "%d");

  bool caught = false;
  try {
    i = to_int(StrFromC("zzz"));
  } catch (ValueError* e) {
    caught = true;
  }
  ASSERT(caught);

  PASS();
}

TEST test_str_contains() {
  bool b;
  Str* s;
  Str* nul;

  log("  str_contains");

  s = StrFromC("foo\0 ", 5);
  ASSERT(str_contains(s, kSpace));

  // this ends with a NUL, but also has a NUL terinator.
  nul = StrFromC("\0", 1);
  ASSERT(str_contains(s, nul));
  ASSERT(!str_contains(kSpace, nul));

  b = str_contains(StrFromC("foo\0a", 5), StrFromC("a"));
  ASSERT(b == true);

  // this ends with a NUL, but also has a NUL terinator.
  s = StrFromC("foo\0", 4);
  b = str_contains(s, StrFromC("\0", 1));
  ASSERT(b == true);

  // Degenerate cases
  b = str_contains(StrFromC(""), StrFromC(""));
  ASSERT(b == true);
  b = str_contains(StrFromC("foo"), StrFromC(""));
  ASSERT(b == true);
  b = str_contains(StrFromC(""), StrFromC("f"));
  ASSERT(b == false);

  // Short circuit
  b = str_contains(StrFromC("foo"), StrFromC("too long"));
  ASSERT(b == false);

  b = str_contains(StrFromC("foo"), StrFromC("oo"));
  ASSERT(b == true);

  b = str_contains(StrFromC("foo"), StrFromC("ood"));
  ASSERT(b == false);

  b = str_contains(StrFromC("foo\0ab", 6), StrFromC("ab"));
  ASSERT(b == true);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(test_str_to_int);
  RUN_TEST(test_str_contains);

  GREATEST_MAIN_END();
  return 0;
}
