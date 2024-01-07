#include "data_lang/j8.h"

//#include "mycpp/runtime.h"
#include "vendor/greatest.h"

void Encode(char* s, int n, int is_j8) {
  unsigned char** in_pos = (unsigned char**)&s;
  // this is big enough
  unsigned char out[64] = {0};

  unsigned char* begin = out;
  unsigned char** out_pos = &begin;

  **out_pos = '"'; (*out_pos)++;

  printf("*in_pos %p *out_pos %p\n", *in_pos, *out_pos);

  int result = 0;
  for (int i = 0; i < n; ++i) {
    result = EncodeRuneOrByte(in_pos, out_pos, is_j8);

    printf("result = %d\n", result);
    //printf("*in_pos %p *out_pos %p\n", *in_pos, *out_pos);
    //printf("\n");
  }

  **out_pos = '"'; (*out_pos)++;
  printf("out = %s\n", out);
}

TEST encode_test() {
  char* s = "hi \x01 ' \" new \n \\ \u03bc";
  int n = strlen(s);

  Encode(s, n, 0);
  Encode(s, n, 1);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  GREATEST_MAIN_BEGIN();

  RUN_TEST(encode_test);

  GREATEST_MAIN_END();
  return 0;
}
