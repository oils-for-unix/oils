#include "data_lang/j8.h"

//#include "mycpp/runtime.h"
#include "vendor/greatest.h"

void Encode(char* s, int n, int is_j8) {
  unsigned char** in_pos = (unsigned char**)&s;
  unsigned char* end = (unsigned char*)s + n;

  // this is big enough
  unsigned char out[64] = {0};

  unsigned char* begin = out;
  unsigned char** out_pos = &begin;

  **out_pos = is_j8 ? '\'' : '"';
  (*out_pos)++;

  printf("*in_pos %p *out_pos %p\n", *in_pos, *out_pos);

  int result = 0;
  while (*in_pos < end) {
    result = EncodeRuneOrByte(in_pos, out_pos, is_j8);

    // printf("result = %d\n", result);
    // printf("*in_pos %p *out_pos %p\n", *in_pos, *out_pos);
    // printf("\n");
  }

  **out_pos = is_j8 ? '\'' : '"';
  (*out_pos)++;
  printf("out = %s\n", out);
  printf("\n");
}

TEST encode_test() {
  char* mixed = "hi \x01 \u4000\xfe\u4001\xff\xfd ' \" new \n \\ \u03bc";
  Encode(mixed, strlen(mixed), 0);
  Encode(mixed, strlen(mixed), 1);

  char* u = "hi \u4000 \u03bc";
  Encode(u, strlen(u), 0);
  Encode(u, strlen(u), 1);

  // Internal NUL
  char* b = "\x00\x01\xff";
  Encode(b, 3, 0);
  Encode(b, 3, 1);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  GREATEST_MAIN_BEGIN();

  RUN_TEST(encode_test);

  GREATEST_MAIN_END();
  return 0;
}
