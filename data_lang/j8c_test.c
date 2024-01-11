#include "data_lang/j8c.h"

#include "data_lang/j8.h"
#include "data_lang/j8_test_lib.h"
#include "vendor/greatest.h"

TEST char_int_test() {
  const char* s = "foo\xff";

  // Python uses Py_CHARMASK() macro to avoid this problem!

  // Like this
  //     int c = Py_CHARMASK(s[i]);

  // Python.h:
  //     #define Py_CHARMASK(c)           ((unsigned char)((c) & 0xff))

  // For j8, let's just use unsigned char and make callers cast.

  int c = s[3];
  printf("c = %c\n", c);
  printf("c = %d\n", c);

  PASS();
}

TEST encode_test() {
  for (int i = 0; J8_TEST_CASES[i]; ++i) {
    const char* s = J8_TEST_CASES[i];
    int input_len = strlen(s);
    j8_buf_t in = {(unsigned char*)s, input_len};

    j8_buf_t result = {0};
    J8EncodeString(in, &result, 0);

    printf("result %s\n", result.data);
    printf("result.len %d\n", result.len);

    // Some sanity checks
    int n = strlen(s);
    switch (n) {
    case 0:  // empty string -> ""
      ASSERT_EQ_FMT(2, result.len, "%d");
      break;
    case 1:  // x -> "x"
      ASSERT_EQ_FMT(3, result.len, "%d");
      break;
    default:
      ASSERT(input_len < result.len);
      break;
    }
    free(result.data);

    // Encode again with J8 fallback
    result = {0};
    J8EncodeString(in, &result, 1);

    printf("result %s\n", result.data);
    printf("result.len %d\n", result.len);
    free(result.data);

    printf("\n");
  }

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  GREATEST_MAIN_BEGIN();

  RUN_TEST(encode_test);
  RUN_TEST(char_int_test);

  GREATEST_MAIN_END();
  return 0;
}
