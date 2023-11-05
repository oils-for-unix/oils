// float_test.cc - Printing floats

#include <inttypes.h>
// #include <limits.h>  // HOST_NAME_MAX
// #include <unistd.h>  // gethostname()

//#include <new>  // placement new

// #include "mycpp/runtime.h"
// #include "mycpp/common.h"
// #include "mycpp/gc_obj.h"  // ObjHeader
#include "vendor/greatest.h"

// https://randomascii.wordpress.com/2012/01/11/tricks-with-the-floating-point-format/

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

void PrintFloat(Float_t num) {
  // printf("Float value, representation, sign, exponent, mantissa\n");
  printf("%1.8e   0x%08X   sign %d, exponent %d, mantissa 0x%06X\n", num.f,
         num.i, num.parts.sign, num.parts.exponent, num.parts.mantissa);
}

TEST print_float_test() {
  Float_t num(1.0f);
  for (int i = 0; i < 10; ++i) {
    PrintFloat(num);
    num.i -= 1;
  }

  PASS();
}

typedef float (*Transform)(float);

// https://randomascii.wordpress.com/2014/01/27/theres-only-four-billion-floatsso-test-them-all/

// Pass in a uint32_t range of float representations to test.
// start and stop are inclusive. Pass in 0, 0xFFFFFFFF to scan all
// floats. The floats are iterated through by incrementing
// their integer representation.
bool ExhaustiveTest(uint32_t start, uint32_t stop, Transform TestFunc,
                    Transform RefFunc, const char* desc) {
  printf("Testing %s from %u to %u (inclusive).\n", desc, start, stop);
  // Use long long to let us loop over all positive integers.
  long long i = start;
  bool passed = true;
  while (i <= stop) {
    Float_t input;
    input.i = (int32_t)i;
    Float_t testValue = TestFunc(input.f);
    Float_t refValue = RefFunc(input.f);
    // If the results don’t match then report an error.
    if (testValue.f != refValue.f &&
        // If both results are NaNs then we treat that as a match.
        (testValue.f == testValue.f || refValue.f == refValue.f)) {
      printf("Input %.9g, expected %.9g, got %1.9g        \n", input.f,
             refValue.f, testValue.f);
      passed = false;
    }

    ++i;
  }
  return passed;
}

float half(float f) {
  return f / 2;
}

float half2(float f) {
#if 0
  if (f == 4242.00) {
    return f + 1;  // see if exhasutive test finds this number
  }
#endif
  return f / 2;
}

TEST round_trip_test() {
  // This is the biggest number that can be represented in
  // both float and int32_t. It’s 2^31-128.
  Float_t maxfloatasint(2147483520.0f);

  // const uint32_t signBit = 0x80000000;

  // Takes 3.5 seconds in opt
  ASSERT(ExhaustiveTest(0, (uint32_t)maxfloatasint.i, half, half2,
                        "exhaustive half"));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  // gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(print_float_test);
  RUN_TEST(round_trip_test);

  // gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
