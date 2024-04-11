/*
This file contains functions to exhaustively test our decoder. We could try
iterating through all 4-byte sequences, although that would require ~4 billion
cases, which is slow and wasteful. A large number of those ~4 billion cases are
uninteresting and do not help to test our decoder. For example, <41 41 41 C0>
("A, A, A, invalid byte") is uninteresting compared to tests for <41> ("A") and
<C0> ("invalid byte").

What are the interesting cases we want to test? To answer that question, let's
note some properties of `decode`:

 1. decode(encode(x)) = x (for a valid Unicode string x) -- "Inverse of
encoding"
 2. decode(x) fails <==> x is not a valid Unicode string

Invariant (1) can be checked by iterating through all U+00 .. U+10FFFF
codepoints (except for surrogates.) Invariant (2) requires that we collect all
possible error states. There are two major classes. I call them "valid bit
distributions" and "invalid bit distributions."

## Checking Valid Bit Distributions

  Table 3-6 from Unicode Standard 15.0.0 Ch3 [0]. UTF-8 bit distribution

+----------------------------+----------+----------+----------+----------+
| Scalar Value               | 1st Byte | 2nd Byte | 3rd Byte | 4th Byte |
+----------------------------+----------+----------+----------+----------+
| 00000000 0xxxxxxx          | 0xxxxxxx |          |          |          |
| 00000yyy yyxxxxxx          | 110yyyyy | 10xxxxxx |          |          |
| zzzzyyyy yyxxxxxx          | 1110zzzz | 10yyyyyy | 10xxxxxx |          |
| 000uuuuu zzzzyyyy yyxxxxxx | 11110uuu | 10uuzzzz | 10yyyyyy | 10xxxxxx |
+----------------------------+----------+----------+----------+----------+

[0]: https://www.unicode.org/versions/Unicode15.0.0/ch03.pdf

This gives 2**7 + 2**11 + 2**16 + 2**21 = 2164864 valid bit distributions.

Of these 0x10FFFF - 2048 + 1 are valid encodings. The rest are one of the
following errors:

Surrogates are the results of encoding codepoints in the range U+D800 to
U+DFFF. This gives a total of 2048 surrogates.

Overlongs take the form:
  1100_000x 10xx_xxxx                       -- 2**7
  1110_0000 100x_xxxx 10xx_xxxx             -- 2**11
  1111_0000 1000_xxxx 10xx_xxxx 10xx_xxxx   -- 2**18

For a total of 264320 overlongs

Over 10FFFF encodings take the form:
  1111_0101 10xx_xxxx 10xx_xxxx 10xx_xxxx   -- 2**18
  1111_0110 10xx_xxxx 10xx_xxxx 10xx_xxxx   -- 2**18
  1111_0111 10xx_xxxx 10xx_xxxx 10xx_xxxx   -- 2**18

For a total 786432 of too large values

To verify, that adds to total of 2164864 values, equal to the number predicted
by our bit distribution.

## Invalid Encodings or Violations of the Bit Distribution

I have enumerated all invalid sequences, *up to the number of bytes required to
determine the validity*:
  10xx_xxxx

  110x_xxxx 0xxx_xxxx
  110x_xxxx 11xx_xxxx

  1110_xxxx 0xxx_xxxx
  1110_xxxx 11xx_xxxx
  1110_xxxx 10xx_xxxx 0xxx_xxxx
  1110_xxxx 10xx_xxxx 11xx_xxxx

  1111_0xxx 0xxx_xxxx
  1111_0xxx 11xx_xxxx
  1111_0xxx 10xx_xxxx 0xxx_xxxx
  1111_0xxx 10xx_xxxx 11xx_xxxx
  1111_0xxx 10xx_xxxx 10xx_xxxx 0xxx_xxxx
  1111_0xxx 10xx_xxxx 10xx_xxxx 11xx_xxxx

  1111_1xxx

This gives 6597192 possible "minimal invalid encoding sequences."

Combining the valid and invalid sequences we have 8762056 "interesting" cases.
This is _much_ lower than 2**32, while still exhaustively testing our
implementations of `decode(x)`. We generate these exhaustive tests for each
decoder in data_lang/utf8_decoder_tests_gen.py, which results in the
_gen/test/utf8/decoder-exhaustive.inc file #include-ed below.
*/

#include <algorithm>

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

enum utf8_decode_result {
  UTF8_DECODE_OK = 0,
  UTF8_DECODE_ERROR = -1,
};

const char *utf8_decode_result_str(int value) {
  switch (value) {
    case UTF8_DECODE_OK: return "UTF8_DECODE_OK";
    case UTF8_DECODE_ERROR: return "UTF8_DECODE_ERROR";
    default: return NULL;
  }
}

/**
 * Decode the next codepoint from a string.
 *
 * Will write to `string` to post-increment and `codepoint` for the result.
 * `codepoint` may not be valid if the result != UTF8_DECODE_OK.
 */
utf8_decode_result bjorn_utf8_next(const uint8_t** string, uint32_t *codepoint) {
  uint32_t state = 0;

  while (decode(&state, codepoint, **string) && **string) {
    *string += 1;
  }

  if (state != UTF8_ACCEPT) {
    return UTF8_DECODE_ERROR;
  }

  *string += 1;

  return UTF8_DECODE_OK;
}

utf8_decode_result crockford_utf8_next(const uint8_t** string, uint32_t *codepoint) {
  const char* s = reinterpret_cast<const char*>(*string);
  utf8_decode_init(s, std::max(strlen(s), 1UL));

  int c = utf8_decode_next();
  switch (c) {
  case UTF8_END:
    return UTF8_DECODE_ERROR;

  case UTF8_ERROR:
    return UTF8_DECODE_ERROR;

  default:
    *codepoint = c;
    *string += utf8_decode_at_index();
    return UTF8_DECODE_OK;
  }
}

// Exhaustive tests for the UTF8 decoder are generated by
// data_lang/utf8_decoder_tests_gen.py when building this file using ninja.
#include "_gen/test/utf8/decoder-exhaustive.inc"

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

uint32_t num_code_points = 0x10FFFF;

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

// Exhaustive DFA testing strategies
//
// All code points: 1,114,112 of them
//
// - Encode them all
// - Decode each byte
//   - end state should be UTF8_ACCEPT, except for 2048 in surrogate range

//   - code point should match
//
// All byte sequences
//
// 1. 256           1-byte sequences
// 2. 63,536        2-byte sequences
//                  - (ASCII, ASCII) will be 25% of these
// 3. 2**24 = 24 Mi 3-byte sequences
//    overlapping cases
//                  1 + 1 + 1
//                  1 + 2
//                  2 + 1
//
// 4. All 2**32 = 4 Gi 4-byte sequences?  Possible but slightly slow
//    maybe explore this in a smarter way

// Generating errors
//
// - enumerate all out of range
//   - UTF-8 can go up to 2*21 - which is 2,097,152
// - enumerate ALL overlong encodings?
//
// - enumerate ALL sequences that correspond to code points in surrogate range
//   - I think they're all 3 bytes long?

TEST exhaustive_test() {
  long sum = 0;

  for (int i = 0; i < (1 << 21); ++i) {
    sum += i;
    // Almost half these are out of range

    // 2048 of them are surrogates!
  }
  printf("code points %ld\n", sum);

  // How many overlong sequences?
  // The key is making the leading byte 0 I think
  // You can also have 2 or 3 leading zero bytes
  //
  // So you can test all these forms:
  //
  // [0 42 43 44] - should be [42 43 44]
  //
  // [0 0 42 43]  - should be [42 43]
  // [0 42 43]
  //
  // [0 0 0 42]   - should be [42]
  // [0 0 42]
  // [0 42]
  //
  // Each continuation byte has 2*6 == 64 values.
  // 2 byte sequences have 2*5 initial choicse
  // 3 byte sequences have 2*4 initial choices
  // 4 byte sequences have 2*3 initial choices

  for (int i = 0; i < (1 << 8); ++i) {
    sum += i;
  }
  printf("1 byte %ld\n", sum);

  for (int i = 0; i < (1 << 16); ++i) {
    sum += i;
  }
  printf("2 byte %ld\n", sum);

  for (int i = 0; i < (1 << 24); ++i) {
    sum += i;
  }
  printf("3 byte %ld\n", sum);

  PASS();
}

TEST enumerate_utf8_test() {
  // Valid digits, and some of them are overlong

  // [a b c d] - 21 bits of info
  int n = 0;
  int overlong = 0;
  for (int a = 0; a < (1 << 3); ++a) {
    for (int b = 0; b < (1 << 6); ++b) {
      for (int c = 0; c < (1 << 6); ++c) {
        for (int d = 0; d < (1 << 6); ++d) {
          n++;
          if (a == 0) {
            overlong++;
          }
        }
      }
    }
  }
  printf("4 byte: n = %10d, overlong = %10d, valid = %10d\n", n, overlong,
         n - overlong);

  // [a b c] - 4 + 6 + 6 = 16 bits of info
  n = 0;
  overlong = 0;
  for (int a = 0; a < (1 << 4); ++a) {
    for (int b = 0; b < (1 << 6); ++b) {
      for (int c = 0; c < (1 << 6); ++c) {
        n++;
        if (a == 0) {
          overlong++;
        }
      }
    }
  }
  printf("3 byte: n = %10d, overlong = %10d, valid = %10d\n", n, overlong,
         n - overlong);

  // [a b] - 5 + 6 = 11 bits of info
  n = 0;
  overlong = 0;
  for (int a = 0; a < (1 << 5); ++a) {
    for (int b = 0; b < (1 << 6); ++b) {
      n++;
      if (a == 0) {
        overlong++;
      }
    }
  }
  printf("2 byte: n = %10d, overlong = %10d, valid = %10d\n", n, overlong,
         n - overlong);

  // Types of errors
  // Surrogate Range
  // Overlong
  //
  // Not covered by this:
  // Invalid sequence (start byte, continuation byte) - we are leaving this off

  n = 0;
  for (int a = 0; a < (1 << 8); ++a) {
    n++;
  }
  printf("1 byte: n = %10d\n", n);

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

#define RUN_EXHAUSTIVE_TEST(decoder)                      \
  RUN_TEST(decoder##_utf8_decoder_identity);              \
  RUN_TEST(decoder##_utf8_decoder_surrogates);            \
  RUN_TEST(decoder##_utf8_decoder_overlong);              \
  RUN_TEST(decoder##_utf8_decoder_too_large);             \
  RUN_TEST(decoder##_utf8_decoder_bad_bit_distribution);

  RUN_EXHAUSTIVE_TEST(bjorn)
  RUN_EXHAUSTIVE_TEST(crockford)

  RUN_TEST(surrogate_test);
  RUN_TEST(loop_all_test);
  RUN_TEST(crockford_test);
  RUN_TEST(enumerate_utf8_test);
  RUN_TEST(exhaustive_test);
  RUN_TEST(decode_all_test);
  RUN_TEST(dfa_test);

  GREATEST_MAIN_END();
  return 0;
}
