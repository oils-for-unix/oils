#include "mycpp/gc_builtins.h"

#include <assert.h>
#include <limits.h>  // INT_MAX
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>   // vprintf

#include "mycpp/gc_dict.h"
#include "mycpp/gc_list.h"
#include "mycpp/gc_tuple.h"
#include "vendor/greatest.h"

GLOBAL_STR(kStrFood, "food");
GLOBAL_STR(kWithNull, "foo\0bar");
GLOBAL_STR(kSpace, " ");

TEST print_test() {
  print(kStrFood);
  print(kWithNull);  // truncates

  PASS();
}

TEST bool_test() {
  ASSERT_EQ(false, to_bool(kEmptyString));
  ASSERT_EQ(true, to_bool(StrFromC("a")));

  ASSERT_EQ(true, to_bool(42));
  ASSERT_EQ(true, to_bool(1));
  ASSERT_EQ(false, to_bool(0));
  ASSERT_EQ(true, to_bool(-42));

  PASS();
}

TEST int_test() {
  ASSERT_EQ(1, to_int(true));
  ASSERT_EQ(0, to_int(false));

  PASS();
}

TEST float_test() {
  ASSERT_EQ(0.0f, to_float(StrFromC("0.0")));

  ASSERT_EQ(0.25f, to_float(StrFromC("0.25")));
  ASSERT_EQ(0.5f, to_float(StrFromC("0.5")));
  ASSERT_EQ(99.0f, to_float(StrFromC("99")));

  ASSERT_EQ(-0.25f, to_float(StrFromC("-0.25")));
  ASSERT_EQ(-0.5f, to_float(StrFromC("-0.5")));
  ASSERT_EQ(-99.0f, to_float(StrFromC("-99")));

  // Note: strtod supports hexadecimal and NaN

  bool caught;

  caught = false;
  try {
    (void)to_float(kEmptyString);
  } catch (ValueError* e) {
    caught = true;
  }
  ASSERT(caught);

  caught = false;
  try {
    (void)to_float(StrFromC("x"));
  } catch (ValueError* e) {
    caught = true;
  }
  ASSERT(caught);

  caught = false;
  try {
    Str* huge = str_repeat(StrFromC("123456789"), 100);
    (void)to_float(huge);
  } catch (ValueError* e) {
    caught = true;
  }
  ASSERT(caught);

  caught = false;
  try {
    Str* zeros = str_repeat(StrFromC("00000000"), 100);
    Str* tiny = str_concat3(StrFromC("0."), zeros, StrFromC("1"));
    (void)to_float(tiny);
  } catch (ValueError* e) {
    caught = true;
  }
  ASSERT(caught);

  PASS();
}

// Wrapper for testing
bool _StrToInteger(Str* s, int* result, int base) {
  return StringToInteger(s->data_, len(s), base, result);
}

TEST StringToInteger_test() {
  int i;
  bool ok;

  ok = _StrToInteger(StrFromC("345"), &i, 10);
  ASSERT(ok);
  ASSERT_EQ_FMT(345, i, "%d");

  // Hack to test slicing.  Truncated "345" at "34".
  ok = _StrToInteger(StrFromC("345", 2), &i, 10);
  ASSERT(ok);
  ASSERT_EQ_FMT(34, i, "%d");

  ok = _StrToInteger(StrFromC("1234567890"), &i, 10);
  ASSERT(ok);
  ASSERT(i == 1234567890);

  // overflow
  ok = _StrToInteger(StrFromC("12345678901234567890"), &i, 10);
  ASSERT(!ok);

  // underflow
  ok = _StrToInteger(StrFromC("-12345678901234567890"), &i, 10);
  ASSERT(!ok);

  // negative
  ok = _StrToInteger(StrFromC("-123"), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Leading space is OK!
  ok = _StrToInteger(StrFromC(" -123"), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Trailing space is OK!
  ok = _StrToInteger(StrFromC(" -123  "), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Empty string isn't an integer
  ok = _StrToInteger(StrFromC(""), &i, 10);
  ASSERT(!ok);

  ok = _StrToInteger(StrFromC("xx"), &i, 10);
  ASSERT(!ok);

  // Trailing garbage
  ok = _StrToInteger(StrFromC("42a"), &i, 10);
  ASSERT(!ok);

  PASS();
}

TEST str_to_int_test() {
  int i;

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

TEST int_to_str_test() {
  Str* int_str;
  int_str = str(INT_MAX);
  ASSERT(str_equals0("2147483647", int_str));

  int_str = str(-INT_MAX);
  ASSERT(str_equals0("-2147483647", int_str));

  int int_min = INT_MIN;
  int_str = str(int_min);
  ASSERT(str_equals0("-2147483648", int_str));

  // Wraps with - sign.  Is this well-defined behavior?
  int_str = str(1 << 31);
  log("i = %s", int_str->data_);

  PASS();
}

TEST comparators_test() {
  log("maybe_str_equals()");
  ASSERT(maybe_str_equals(kEmptyString, kEmptyString));
  ASSERT(!maybe_str_equals(kEmptyString, nullptr));
  ASSERT(maybe_str_equals(nullptr, nullptr));

  // TODO: check for this bug elsewhere
  log("Tuple2<Str*, int> are_equal()");
  auto t1 = Alloc<Tuple2<Str*, int>>(StrFromC("42"), 42);
  auto t2 = Alloc<Tuple2<Str*, int>>(StrFromC("42"), 42);
  auto t3 = Alloc<Tuple2<Str*, int>>(StrFromC("99"), 99);

  ASSERT(are_equal(t1, t2));
  ASSERT(!are_equal(t2, t3));

  PASS();
}

TEST exceptions_test() {
  auto v1 = Alloc<ValueError>();
  ASSERT_EQ(HeapTag::FixedSize, v1->header_.heap_tag);

  auto v2 = Alloc<ValueError>(kEmptyString);
  ASSERT_EQ(HeapTag::FixedSize, v2->header_.heap_tag);

  IndexError* other;
  bool caught = false;
  try {
    throw Alloc<IndexError>();
  } catch (IndexError* e) {
    log("e %p", e);
    other = e;
    caught = true;
  }

  log("other %p", other);
  ASSERT(caught);

  caught = false;
  try {
    throw Alloc<OSError>(99);
  } catch (IOError_OSError* e) {
    caught = true;
  }
  ASSERT(caught);

  // TODO: Make this work with return value rooting
  RuntimeError* r = nullptr;
  Str* message = nullptr;
  StackRoots _roots2({&r, &message});
  message = StrFromC("libc::regex_match");

  caught = false;
  try {
    r = Alloc<RuntimeError>(message);
    throw r;

  } catch (RuntimeError* e) {
    caught = true;

    log("RuntimeError %s", e->message->data());
  }
  ASSERT(caught);

  auto u = Alloc<UnicodeError>(StrFromC("libc"));
  (void)u;

  auto i = Alloc<IOError>(0);
  (void)i;

  PASS();
}

TEST hash_str_test() {
  // two strings known not to collide ahead of time
  Str* a = StrFromC("foobarbaz");
  Str* b = StrFromC("123456789");
  ASSERT(hash(a) != hash(b));

  PASS();
}

TEST max_test() {
  ASSERT(max(-1, 0) == 0);
  ASSERT(max(0, -1) == max(-1, 0));
  ASSERT(max(42, 13) == 42);

  auto* ints = NewList<int>(std::initializer_list<int>{13, 0, 42, -1});
  ASSERT(max(ints) == 42);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(print_test);

  RUN_TEST(bool_test);
  RUN_TEST(int_test);
  RUN_TEST(float_test);

  RUN_TEST(StringToInteger_test);
  RUN_TEST(str_to_int_test);
  RUN_TEST(int_to_str_test);

  RUN_TEST(comparators_test);

  RUN_TEST(exceptions_test);

  RUN_TEST(hash_str_test);

  RUN_TEST(max_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */

  return 0;
}
