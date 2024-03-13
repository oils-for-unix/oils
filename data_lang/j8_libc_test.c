#include "data_lang/j8_libc.h"

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

TEST j8_encode_test() {
  for (int i = 0; J8_TEST_CASES[i]; ++i) {
    const char* s = J8_TEST_CASES[i];
    int input_len = strlen(s);
    j8_buf_t in = {(unsigned char*)s, input_len};

    // printf("input '%s' %d\n", in.data, input_len);

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
    case 1: {  // x -> "x"
      unsigned char ch = s[0];
      if (ch < 128) {
        ASSERT_EQ_FMT(3, result.len, "%d");
      }
      break;
    }
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

TEST shell_encode_test() {
  for (int i = 0; J8_TEST_CASES[i]; ++i) {
    const char* s = J8_TEST_CASES[i];
    int input_len = strlen(s);
    j8_buf_t in = {(unsigned char*)s, input_len};

    // printf("input '%s' %d\n", in.data, input_len);

    j8_buf_t result = {0};
    ShellEncodeString(in, &result, 0);

    printf("result %s\n", result.data);
    printf("result.len %d\n", result.len);

    // Some sanity checks
    int n = strlen(s);
    switch (n) {
    case 0:  // empty string -> ""
      ASSERT_EQ_FMT(2, result.len, "%d");
      break;
    case 1: {  // x -> "x"
      unsigned char ch = s[0];
      if (ch < 128) {
        ASSERT_EQ_FMT(3, result.len, "%d");
      }
    } break;
    default:
      ASSERT(input_len < result.len);
      break;
    }
    free(result.data);

    // Encode again with J8 fallback
    result = {0};
    ShellEncodeString(in, &result, 1);  // YSH fallback

    printf("result %s\n", result.data);
    printf("result.len %d\n", result.len);
    free(result.data);

    printf("\n");
  }

  PASS();
}

TEST invalid_utf8_test() {
  {
    // Truncated, should not have \x00 on the end
    const char* s = "\xce";

    j8_buf_t in = {(unsigned char*)s, strlen(s)};
    j8_buf_t result = {0};
    ShellEncodeString(in, &result, 0);

    printf("%s\n", result.data);
    ASSERT_EQ(0, memcmp("$'\\xce'", result.data, result.len));
    free(result.data);

    J8EncodeString(in, &result, 1);
    printf("%s\n", result.data);
    ASSERT_EQ(0, memcmp("b'\\yce'", result.data, result.len));
    free(result.data);
  }

  {
    // \U0001f926 with bad byte at the end
    const char* s = "\xf0\x9f\xa4\xff";

    j8_buf_t in = {(unsigned char*)s, strlen(s)};
    j8_buf_t result = {0};
    ShellEncodeString(in, &result, 0);

    printf("%s\n", result.data);
    ASSERT_EQ(0, memcmp("$'\\xf0\\x9f\\xa4\\xff'", result.data, result.len));
    free(result.data);

    J8EncodeString(in, &result, 1);
    printf("%s\n", result.data);
    ASSERT_EQ(0, memcmp("b'\\yf0\\y9f\\ya4\\yff'", result.data, result.len));
    free(result.data);
  }

  PASS();
}

TEST all_bytes_test() {
  char s[2];
  s[1] = '\0';
  for (int i = 0; i < 256; ++i) {
    s[0] = i;

    j8_buf_t in = {(unsigned char*)s, 1};
    j8_buf_t result = {0};
    ShellEncodeString(in, &result, 0);

    printf("i %d -> %s\n", i, result.data);
    free(result.data);

    J8EncodeString(in, &result, 1);
    // printf("i %d -> %s\n", i, result.data);
    free(result.data);
  }

  PASS();
}

TEST can_omit_quotes_test() {
  const char* s = "foo";
  ASSERT(CanOmitQuotes((unsigned char*)s, strlen(s)));

  s = "foo bar";
  ASSERT(!CanOmitQuotes((unsigned char*)s, strlen(s)));

  s = "my-dir/my_file.cc";
  ASSERT(CanOmitQuotes((unsigned char*)s, strlen(s)));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  GREATEST_MAIN_BEGIN();

  RUN_TEST(j8_encode_test);
  RUN_TEST(shell_encode_test);
  RUN_TEST(invalid_utf8_test);
  RUN_TEST(all_bytes_test);
  RUN_TEST(char_int_test);
  RUN_TEST(can_omit_quotes_test);

  GREATEST_MAIN_END();
  return 0;
}
