#include "mycpp/gc_mops.h"

#include <cinttypes>

#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST bigint_test() {
  // You need to instantiate it as a BigInt, the constant (1) doesn't work
  // And also use %ld

  mops::BigInt i = mops::BigInt{1} << 31;
  log("bad  i = %d", i);  // bug
  log("good i = %ld", i);
  log("");

  mops::BigInt i2 = mops::BigInt{1} << 32;
  log("good i2 = %ld", i2);
  log("");

  mops::BigInt i3 = i2 + i2;
  log("good i3 = %ld", i3);
  log("");

  int64_t j = int64_t{1} << 31;
  log("bad  j = %d", j);  // bug
  log("good j = %ld", j);

  PASS();
}

TEST static_cast_test() {
  // These conversion ops are currently implemented by static_cast<>

  auto big = mops::BigInt{1} << 31;

  // Turns into a negative number
  int i = mops::BigTruncate(big);
  log("i = %d", i);

  // Truncates float to int.  TODO: Test out Oils behavior.
  float f = 3.14f;
  auto fbig = mops::FromFloat(f);
  log("%f -> %ld", f, fbig);

  f = 3.99f;
  fbig = mops::FromFloat(f);
  log("%f = %ld", f, fbig);

  // OK this is an exact integer
  f = mops::ToFloat(big);
  log("f = %f", f);
  ASSERT_EQ_FMT(f, 2147483648.0, "%f");

  PASS();
}

TEST conversion_test() {
  mops::BigInt int_min{INT64_MIN};
  mops::BigInt int_max{INT64_MAX};
  BigStr* int_str;

  int_str = mops::ToStr(15);
  ASSERT(str_equals0("15", int_str));
  print(mops::ToStr(int_min));
  print(mops::ToStr(int_max));
  print(kEmptyString);

  int_str = mops::ToOctal(15);
  ASSERT(str_equals0("17", int_str));
  print(mops::ToOctal(int_min));
  print(mops::ToOctal(int_max));
  print(kEmptyString);

  int_str = mops::ToHexLower(15);
  ASSERT(str_equals0("f", int_str));
  print(mops::ToHexLower(int_min));
  print(mops::ToHexLower(int_max));
  print(kEmptyString);

  int_str = mops::ToHexUpper(15);
  ASSERT(str_equals0("F", int_str));
  print(mops::ToHexUpper(int_min));
  print(mops::ToHexUpper(int_max));
  print(kEmptyString);

  PASS();
}

TEST float_test() {
  double f = mops::ToFloat(1) / mops::ToFloat(3);
  // double f = static_cast<double>(1) / static_cast<double>(3);

  log("one third = %f", f);
  // wtf, why does this has a 43
  log("one third = %.9g", f);
  log("one third = %.10g", f);
  log("one third = %.11g", f);

  f = mops::ToFloat(2) / mops::ToFloat(3);
  log("one third = %.9g", f);
  log("one third = %.10g", f);

  double one = mops::ToFloat(1);
  double three = mops::ToFloat(3);
  log("one = %.10g", one);
  log("three = %.10g", three);
  log("one / three = %.10g", one / three);

  PASS();
}

TEST gcc_clang_overflow_test() {
  bool ok;

  // Compute (1L << 63) - 1L without overflow!
  int64_t a = INT64_C(1) << 62;
  a += (INT64_C(1) << 62) - INT64_C(1);

  int64_t b = 0;
  int64_t result = 0;

  for (b = 0; b <= 1; ++b) {
#if LONG_MAX == INT64_MAX
    ok = __builtin_saddl_overflow(a, b, &result);
#else
    // 32-bit, we have to use long long?
    ok = __builtin_saddll_overflow(a, b, &result);
#endif
    if (ok) {
      printf("%" PRId64 " + %" PRId64 " = signed add long overflow!\n", a, b);
    } else {
      printf("%" PRId64 " + %" PRId64 " = %" PRId64 "\n", a, b, result);
    }
  }

  a = INT64_C(1) << 62;
  for (b = 1; b <= 2; ++b) {
#if LONG_MAX == INT64_MAX
    ok = __builtin_smull_overflow(a, b, &result);
#else
    ok = __builtin_smulll_overflow(a, b, &result);
#endif

    if (ok) {
      printf("%" PRId64 " * %" PRId64 " = signed mul long overflow!\n", a, b);
    } else {
      printf("%" PRId64 " * %" PRId64 " = %" PRId64 "\n", a, b, result);
    }
  }

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(bigint_test);
  RUN_TEST(static_cast_test);
  RUN_TEST(conversion_test);
  RUN_TEST(float_test);
  RUN_TEST(gcc_clang_overflow_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();

  return 0;
}
