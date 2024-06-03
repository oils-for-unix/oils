// float_test.cc - Learning by running code from Bruce Dawson's articles!
//
// Index here:
//   https://randomascii.wordpress.com/2013/02/07/float-precision-revisited-nine-digit-float-portability/
//
// union Float_t helper:
//   https://randomascii.wordpress.com/2012/01/11/tricks-with-the-floating-point-format/
//
// How to round trip floating numbers - just sprintf() and sscanf!
//   https://randomascii.wordpress.com/2012/03/08/float-precisionfrom-zero-to-100-digits-2/
//
//     printf(“%1.8e\n”, d); // Round-trippable float, always with an exponent
//     printf(“%.9g\n”, d); // Round-trippable float, shortest possible
//
//     printf(“%1.16e\n”, d); // Round-trippable double, always with an exponent
//     printf(“%.17g\n”, d); // Round-trippable double, shortest possible
//
// Good idea - do an exhaustive test of all floats:
//   https://randomascii.wordpress.com/2014/01/27/theres-only-four-billion-floatsso-test-them-all/
//
// But use threads.  A single threaded test took 12 minutes on my machine.
//   https://randomascii.wordpress.com/2012/03/11/c-11-stdasync-for-fast-float-format-finding/

#include <inttypes.h>

#include "vendor/greatest.h"

union Float_t {
  Float_t(float num = 0.0f) : f(num) {
  }
  // Portable extraction of components.
  bool Negative() const {
    return (i >> 31) != 0;
  }
  int32_t RawMantissa() const {
    return i & ((1 << 23) - 1);
  }
  int32_t RawExponent() const {
    return (i >> 23) & 0xFF;
  }

  int32_t i;
  float f;
#if 1
  struct {  // Bitfields for exploration. Do not use in production code.
    uint32_t mantissa : 23;
    uint32_t exponent : 8;
    uint32_t sign : 1;
  } parts;
#endif
};

void PrintPartsOfFloat(Float_t num) {
  // printf("Float value, representation, sign, exponent, mantissa\n");
  printf("%1.8e   0x%08X   sign %d, exponent %d, mantissa 0x%06X\n", num.f,
         num.i, num.parts.sign, num.parts.exponent, num.parts.mantissa);
}

// https://randomascii.wordpress.com/2013/02/07/float-precision-revisited-nine-digit-float-portability/

TEST print_float_test() {
  Float_t num(1.0f);
  for (int i = 0; i < 10; ++i) {
    PrintPartsOfFloat(num);

    // change it to an adjacent float
    num.i -= 1;

#if 0
    char s[20];

    // He recommends both of these - what is the difference?
    // Oh one of them uses e-01

    sprintf(s, "%1.8e\n", num.f);
    printf("%s", s);

    sprintf(s, "%.9g\n", num.f);
    printf("%s", s);

    float f;
    sscanf(s, "%f", &f);
    Float_t parsed(f);

    sprintf(s, "%.9g\n", parsed.f);
    printf("parsed %s", s);

    ASSERT_EQ_FMT(num.i, parsed.i, "%d");
#endif
  }

  PASS();
}

TEST decimal_round_trip_test() {
  // Test that sprintf() and sscanf() round trip all floats!
  // Presumably strtof() uses the same algorithm as sscanf().

  // This is the biggest number that can be represented in both float and
  // int32_t. It’s 2^31-128.
  Float_t max_float(2147483520.0f);

  // 22 bits out of 32, so we print 2**10 or ~1000 lines of progress
  const int interval = 1 << 22;

  // Use long long to let us loop over all positive integers.
  long long i = 0;
  while (i <= max_float.i) {
    Float_t num;
    num.i = (int32_t)i;

    char s[20];
    sprintf(s, "%.9g\n", num.f);  // preserves all information
    // printf("%s", s);

    float f;
    sscanf(s, "%f", &f);  // recover all information
    Float_t parsed(f);

    sprintf(s, "%.9g\n", parsed.f);
    // printf("parsed %s", s);

    ASSERT_EQ_FMT(num.i, parsed.i, "%d");

    i++;

    if (i % interval == 0) {
      printf("%lld iterations done\n", i);
    }

    // Comment this out to do more
    if (i == 1000) {
      printf("STOPPING EARLY\n");
      break;
    }
  }
  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  GREATEST_MAIN_BEGIN();

  RUN_TEST(print_float_test);
  RUN_TEST(decimal_round_trip_test);

  GREATEST_MAIN_END();
  return 0;
}
