#include <inttypes.h>

#include "data_lang/utf8_impls/bjoern_dfa.h"
#include "data_lang/utf8_impls/utf8_decode.h"

//#include "mycpp/runtime.h"
#include "vendor/greatest.h"

// Copied from UTF-8 proc
// https://github.com/JuliaStrings/utf8proc/blob/master/utf8proc.c#L177

int utf8proc_encode_char(uint32_t uc, uint8_t* dst) {
  if (uc < 0x80) {
    dst[0] = (uint8_t)uc;
    return 1;
  } else if (uc < 0x800) {
    dst[0] = (uint8_t)(0xC0 + (uc >> 6));
    dst[1] = (uint8_t)(0x80 + (uc & 0x3F));
    return 2;
    // Note: we allow encoding 0xd800-0xdfff here, so as not to change
    // the API, however, these are actually invalid in UTF-8
  } else if (uc < 0x10000) {
    dst[0] = (uint8_t)(0xE0 + (uc >> 12));
    dst[1] = (uint8_t)(0x80 + ((uc >> 6) & 0x3F));
    dst[2] = (uint8_t)(0x80 + (uc & 0x3F));
    return 3;
  } else if (uc < 0x110000) {
    dst[0] = (uint8_t)(0xF0 + (uc >> 18));
    dst[1] = (uint8_t)(0x80 + ((uc >> 12) & 0x3F));
    dst[2] = (uint8_t)(0x80 + ((uc >> 6) & 0x3F));
    dst[3] = (uint8_t)(0x80 + (uc & 0x3F));
    return 4;
  } else
    return 0;
}

void printCodePoints(const uint8_t* s) {
  uint32_t codepoint;
  uint32_t state = 0;

  for (; *s; ++s)
    if (!decode(&state, &codepoint, *s)) {
      printf("U+%04X\n", codepoint);
    }

  if (state != UTF8_ACCEPT) printf("The string is not well-formed\n");
}

TEST dfa_test() {
  const char* s = "hello\u03bc";
  printCodePoints(reinterpret_cast<const uint8_t*>(s));

  PASS();
}

uint32_t num_code_points = 17 * 1 << 16;

// uint32_t num_code_points = 1 << 21;  // DFA has 983,040 disagreements

TEST decode_all_test() {
  int num_disagree = 0;
  int num_reject = 0;

  // 17 "planes" of 2^16 - https://en.wikipedia.org/wiki/Unicode
  // UTF-8 can represent more numbers (up to 21 bits), but this state machine
  // doesn't need to handle them.

  uint64_t sum_codepoint = 0;

  for (uint32_t i = 0; i < num_code_points; ++i) {
    uint8_t bytes[4] = {0};
    int num_bytes = utf8proc_encode_char(i, bytes);
    // printf("i = %d, num_bytes = %d\n", i, num_bytes);

    uint32_t state = 0;
    uint32_t codepoint = 0;
    for (int j = 0; j < num_bytes; ++j) {
      decode(&state, &codepoint, bytes[j]);
    }
    if (state == UTF8_ACCEPT) {
      ASSERT_EQ_FMT(i, codepoint, "%d");
      if (i != codepoint) {
        num_disagree += 1;
      }
    } else {
      num_reject += 1;
    }

    sum_codepoint += i;
  }

  printf("sum_codepoint = %ld\n", sum_codepoint);
  printf("num_disagree = %d\n", num_disagree);
  printf("num_reject = %d\n", num_reject);

  PASS();
}

TEST crockford_test() {
  char* s = const_cast<char*>("hello\u03bc");
  utf8_decode_init(s, strlen(s));

  int c;
  bool done = false;
  while (!done) {
    c = utf8_decode_next();

    switch (c) {
    case UTF8_END:
      done = true;
      break;

    case UTF8_ERROR:
      printf("decode error");
      break;

    default:
      printf("U+%04X\n", c);
      break;
    }
  }

  PASS();
}

TEST loop_all_test() {
  int sum = 0;
  int sum_codepoint = 0;

  int num_errors = 0;

  // Takes 1.4 seconds to iterate through all possibilities
  for (uint32_t i = 0;; ++i) {
    /*
        uint32_t state = 0;
        uint32_t codepoint = 0;

        uint8_t* bytes = reinterpret_cast<uint8_t*>(&i);
        int result = decode(&state, &codepoint, bytes[0]);

        if (result == UTF8_REJECT) {
          num_errors += 1;
        } else {
          sum_codepoint += codepoint;
        }
    */
    sum += i;

    if (i == 0xFFFFFFFF) {  // Can't test this condition in the loop
      break;
    }
  }
  printf("sum %d\n", sum);
  printf("sum_codepoint %d\n", sum_codepoint);
  printf("num_errors %d\n", num_errors);
  printf("2 ^21 = %d\n", 1 << 21);

  PASS();
}

void PrintStates(const uint8_t* s) {
  uint32_t codepoint;
  uint32_t state = UTF8_ACCEPT;

  int n = strlen(reinterpret_cast<const char*>(s));
  for (int i = 0; i < n; ++i) {
    decode(&state, &codepoint, s[i]);
    printf("state %d = %d\n", i, state);
  }
}

TEST surrogate_test() {
  // \ud83e
  printf("    surrogate in utf-8\n");
  const uint8_t* s = reinterpret_cast<const uint8_t*>("\xed\xa0\xbe");
  PrintStates(s);

  // mu
  printf("    mu in utf-8\n");
  const uint8_t* t = reinterpret_cast<const uint8_t*>("\xce\xbc");
  PrintStates(t);

  PASS();
}


GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  GREATEST_MAIN_BEGIN();

  RUN_TEST(dfa_test);
  RUN_TEST(decode_all_test);
  RUN_TEST(crockford_test);
  RUN_TEST(surrogate_test);

  GREATEST_MAIN_END();
  return 0;
}
