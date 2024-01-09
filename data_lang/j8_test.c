#include "data_lang/j8.h"

#include "vendor/greatest.h"

// Fixed for now
struct Buf {
  unsigned char* data;
  int capacity;
  int len;
};

void Encode(char* s, int n, Buf* buf, int is_j8) {
  char* orig_s = s;  // save for rewinding

  unsigned char** in = (unsigned char**)&s;
  unsigned char* input_end = (unsigned char*)s + n;

  unsigned char* p = buf->data;           // mutated
  unsigned char* orig_begin = buf->data;  // not mutated
  unsigned char** out = &p;

  J8_OUT('"');
  // printf("*in %p *out %p\n", *in, *out);

  int invalid_utf8 = 0;
  while (*in < input_end) {
    // printf("1 *in %p *out %p\n", *in, *out);

    // TODO: check *out vs. capacity and maybe grow buffer
    invalid_utf8 = EncodeRuneOrByte(in, out, 0);  // JSON escaping

    // Try again with J8 escaping
    if (invalid_utf8 && is_j8) {
      *in = (unsigned char*)orig_s;
      *out = orig_begin;

      J8_OUT('b');
      J8_OUT('\'');

      // TODO: check *out vs. capacity and maybe grow buffer

      while (*in < input_end) {
        // printf("2 *in %p *out %p\n", *in, *out);
        EncodeRuneOrByte(in, out, 1);  // Now with J8 escaping
      }

      J8_OUT('\'');
      buf->len = *out - orig_begin;
      return;
    }
  }

  J8_OUT('"');
  buf->len = *out - orig_begin;
}

void EncodeAndPrint(char* s, int n, int is_j8) {
  Buf buf = {0};
  buf.data = (unsigned char*)malloc(64);
  buf.capacity = 64;

  Encode(s, n, &buf, is_j8);
  buf.data[buf.len] = '\0';  // NUL terminate

  printf("out = %s\n", buf.data);
  free(buf.data);
}

TEST encode_test() {
  char* mixed = "hi \x01 \u4000\xfe\u4001\xff\xfd ' \" new \n \\ \u03bc";
  EncodeAndPrint(mixed, strlen(mixed), 0);
  EncodeAndPrint(mixed, strlen(mixed), 1);

  char* u = "hi \u4000 \u03bc";
  EncodeAndPrint(u, strlen(u), 0);
  EncodeAndPrint(u, strlen(u), 1);

  // Internal NUL
  char* b = "\x00\x01\xff";
  EncodeAndPrint(b, 3, 0);
  EncodeAndPrint(b, 3, 1);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  GREATEST_MAIN_BEGIN();

  RUN_TEST(encode_test);

  GREATEST_MAIN_END();
  return 0;
}
