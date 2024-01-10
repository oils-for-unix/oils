#include "data_lang/j8c.h"

#include "data_lang/j8.h"
#include "vendor/greatest.h"

TEST char_int_test() {
  char* s = "foo\xff";

  // Python uses Py_CHARMASK() macro to avoid this problem!

  // Like this
  //     int c = Py_CHARMASK(s[i]);

  // Python.h:
  //     #define Py_CHARMASK(c)           ((unsigned char)((c) & 0xff))

  // For j8, let's just use unsigned char and make callers cast.

  int c = s[3];
  printf("c = %c\n", c);
  printf("c = %d\n", c);
}

TEST encode_test() {
  EncodeString(NULL, 3, NULL, NULL, 1);

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
