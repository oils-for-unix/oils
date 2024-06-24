#include "mycpp/gc_builtins.h"

#include <assert.h>
#include <limits.h>  // INT_MAX
#include <math.h>    // INFINITY
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>   // vprintf

#include "mycpp/gc_dict.h"
#include "mycpp/gc_list.h"
#include "mycpp/gc_tuple.h"
#include "mycpp/test_common.h"
#include "vendor/greatest.h"

GLOBAL_STR(kStrFood, "food");
GLOBAL_STR(kWithNull, "foo\0bar");
GLOBAL_STR(kSpace, " ");

TEST print_test() {
  print(kStrFood);
  print(kWithNull);  // truncates

  PASS();
}

TEST repr_test() {
  print(repr(StrFromC("")));
  print(repr(StrFromC("hi\n")));

  // Hm we're not printing \y00 here, could do that I suppose.
  // This function is used for error messages.
  print(repr(StrFromC("\x02 foo bar \xff \xfe \t")));

  // Uses double quotes
  print(repr(StrFromC("this isn't cool")));

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
  ASSERT_EQ(0.0f, to_float(0));
  ASSERT_EQ(1.0f, to_float(1));
  ASSERT_EQ(42.0f, to_float(42));
  ASSERT_EQ(-42.0f, to_float(-42));

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

  BigStr* huge = str_repeat(StrFromC("123456789"), 100);
  double d = to_float(huge);
  ASSERT_EQ(INFINITY, d);

  double d2 = to_float(StrFromC("-1e309"));
  ASSERT_EQ(-INFINITY, d2);

  BigStr* zeros = str_repeat(StrFromC("00000000"), 100);
  BigStr* tiny = str_concat3(StrFromC("0."), zeros, StrFromC("1"));
  double d3 = to_float(tiny);
  log("d3 = %.17g", d3);
  ASSERT_EQ(0.0f, d3);

  BigStr* neg_tiny = str_concat3(StrFromC("-0."), zeros, StrFromC("1"));
  double d4 = to_float(neg_tiny);
  log("d4 = %.17g", d4);
  ASSERT_EQ(-0.0f, d4);

  PASS();
}

// Wrapper for testing
bool _StringToInt64(BigStr* s, int64_t* result, int base) {
  return StringToInt64(s->data_, len(s), base, result);
}

TEST StringToInteger_test() {
  int64_t i;
  bool ok;

  // Empirically this is 4 4 8 on 32-bit and 4 8 8 on 64-bit
  // We want the bigger numbers
#if 0
  log("sizeof(int) = %d", sizeof(int));
  log("sizeof(long) = %ld", sizeof(long));
  log("sizeof(long long) = %ld", sizeof(long long));
  log("");
  log("LONG_MAX = %ld", LONG_MAX);
  log("LLONG_MAX = %lld", LLONG_MAX);
#endif

  ok = _StringToInt64(StrFromC("345"), &i, 10);
  ASSERT(ok);
  ASSERT_EQ_FMT((int64_t)345, i, "%ld");

  // Hack to test slicing.  Truncated "345" at "34".
  ok = _StringToInt64(StrFromC("345", 2), &i, 10);
  ASSERT(ok);
  ASSERT_EQ_FMT((int64_t)34, i, "%ld");

  ok = _StringToInt64(StrFromC("12345678909"), &i, 10);
  ASSERT(ok);
  ASSERT_EQ_FMT((int64_t)12345678909, i, "%ld");

  // overflow
  ok = _StringToInt64(StrFromC("12345678901234567890"), &i, 10);
  ASSERT(!ok);

  // underflow
  ok = _StringToInt64(StrFromC("-12345678901234567890"), &i, 10);
  ASSERT(!ok);

  // negative
  ok = _StringToInt64(StrFromC("-123"), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Leading space is OK!
  ok = _StringToInt64(StrFromC("\n\t -123"), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Trailing space is OK!
  ok = _StringToInt64(StrFromC(" -123  \t\n"), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // \v is not space
  ok = _StringToInt64(StrFromC(" -123  \v"), &i, 10);
  ASSERT(!ok);

  // Empty string isn't an integer
  ok = _StringToInt64(StrFromC(""), &i, 10);
  ASSERT(!ok);

  ok = _StringToInt64(StrFromC("xx"), &i, 10);
  ASSERT(!ok);

  // Trailing garbage
  ok = _StringToInt64(StrFromC("42a"), &i, 10);
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
  BigStr* int_str;
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

TEST float_to_str_test() {
  BigStr* s = str(3.0);
  ASSERT(str_equals0("3.0", s));
  log("s = %s", s->data_);

  double f = 3.5;
  s = str(f);
  ASSERT(str_equals0("3.5", s));
  log("s = %s", s->data_);

  PASS();
}

TEST comparators_test() {
  log("maybe_str_equals()");
  ASSERT(maybe_str_equals(kEmptyString, kEmptyString));
  ASSERT(!maybe_str_equals(kEmptyString, nullptr));
  ASSERT(maybe_str_equals(nullptr, nullptr));

  // Compare by VALUE, not by pointer.
  // TODO: check for this bug elsewhere
  log("Tuple2<BigStr*, int> items_equal()");
  auto t1 = Alloc<Tuple2<BigStr*, int>>(StrFromC("42"), 42);
  auto t2 = Alloc<Tuple2<BigStr*, int>>(StrFromC("42"), 42);
  auto t3 = Alloc<Tuple2<BigStr*, int>>(StrFromC("99"), 99);

  ASSERT(items_equal(t1, t2));
  ASSERT(!items_equal(t2, t3));

  PASS();
}

TEST container_test() {
  //
  // User-defined class
  //

  // We used Dict<Token*, V> to get rid of the span_id, e.g. for --tool ysh-ify
  auto* dp = Alloc<Dict<Point*, BigStr*>>();
  for (int i = 0; i < 32; ++i) {
    Point* p2 = Alloc<Point>(42, 43);
    dp->set(p2, kEmptyString);
  }
  ASSERT_EQ_FMT(32, len(dp), "%d");

  // For now, we're not allowed to compare lists by pointers.
#if 0
  auto* lp = Alloc<List<Point*>>();
  lp->append(Alloc<Point>(0, 1));
  lp->append(Alloc<Point>(2, 3));
  ASSERT(!list_contains(lp, Alloc<Point>(4, 5)));
#endif

  //
  // int
  //
  auto* di = Alloc<Dict<int, BigStr*>>();
  for (int i = 0; i < 32; ++i) {
    int p2 = 1 << i;
    di->set(p2, kEmptyString);
  }
  ASSERT_EQ_FMT(32, len(di), "%d");

  auto* li = Alloc<List<int>>();
  li->append(1 << 30);
  li->append(1 << 31);
  ASSERT(!list_contains(li, 0));

  //
  // mops::BigInt
  //

  // Failed before we had keys_equal() for mops::BigInt
  auto* d = Alloc<Dict<mops::BigInt, BigStr*>>();
  for (int i = 0; i < 64; ++i) {
    mops::BigInt p2 = mops::BigInt{1} << i;
    d->set(p2, kEmptyString);
  }
  ASSERT_EQ_FMT(64, len(d), "%d");

  // Failed before we had items_equal() for mops::BigInt
  auto* lb = Alloc<List<mops::BigInt>>();
  lb->append(mops::BigInt{1} << 32);
  lb->append(mops::BigInt{1} << 33);
  ASSERT(!list_contains(lb, mops::BigInt{0}));

  PASS();
}

TEST exceptions_test() {
  auto v1 = Alloc<ValueError>();
  ASSERT_EQ(HeapTag::FixedSize, ObjHeader::FromObject(v1)->heap_tag);

  auto v2 = Alloc<ValueError>(kEmptyString);
  ASSERT_EQ(HeapTag::FixedSize, ObjHeader::FromObject(v2)->heap_tag);

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
  BigStr* message = nullptr;
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
  BigStr* a = StrFromC("foobarbaz");
  BigStr* b = StrFromC("123456789");
  ASSERT(hash(a) != hash(b));

  PASS();
}

TEST intern_test() {
  BigStr* s = StrFromC("foo");
  BigStr* t = intern(s);

  ASSERT(str_equals(s, t));

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
  RUN_TEST(repr_test);

  RUN_TEST(bool_test);
  RUN_TEST(int_test);
  RUN_TEST(float_test);

  RUN_TEST(StringToInteger_test);
  RUN_TEST(str_to_int_test);
  RUN_TEST(int_to_str_test);
  RUN_TEST(float_to_str_test);

  RUN_TEST(comparators_test);
  RUN_TEST(container_test);

  RUN_TEST(exceptions_test);

  RUN_TEST(hash_str_test);
  RUN_TEST(intern_test);

  RUN_TEST(max_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */

  return 0;
}
