#include "data_lang/j8.h"

//#include "mycpp/runtime.h"
#include "vendor/greatest.h"

void Encode(char* s, int n, int is_j8) {
  char* orig_s = s;

  unsigned char** in_pos = (unsigned char**)&s;
  unsigned char* end = (unsigned char*)s + n;

  // this is big enough
  unsigned char out[64] = {0};

  unsigned char* begin = out;
  unsigned char* orig_begin = out;
  unsigned char** out_pos = &begin;

  **out_pos = '"';
  (*out_pos)++;

  printf("s %p out %p\n", s, out);
  //printf("*in_pos %p *out_pos %p\n", *in_pos, *out_pos);

  int invalid_utf8 = 0;
  while (*in_pos < end) {
    //printf("1 *in_pos %p *out_pos %p\n", *in_pos, *out_pos);

    invalid_utf8 = EncodeRuneOrByte(in_pos, out_pos, 0);  // JSON escaping

    // Try again with J8 escaping
    if (invalid_utf8 && is_j8) {
      *in_pos = (unsigned char*)orig_s;
      *out_pos = orig_begin;

      **out_pos = 'b';
      (*out_pos)++;

      **out_pos = '\'';
      (*out_pos)++;

      while (*in_pos < end) {
        //printf("2 *in_pos %p *out_pos %p\n", *in_pos, *out_pos);
        EncodeRuneOrByte(in_pos, out_pos, 1);  // Now with J8 escaping
      }

      **out_pos = '\'';
      (*out_pos)++;

      printf("out = %s\n", out);
      printf("\n");
      return;
    }
  }

  **out_pos = '"';
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
