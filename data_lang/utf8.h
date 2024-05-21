#ifndef DATA_LANG_UTF8_H
#define DATA_LANG_UTF8_H

#include <stddef.h>  // size_t
#include <stdint.h>  // uint32_t
#include <stdio.h>

/**
 *              ---- Quick reference about the encoding ----
 *
 * First, all valid UTF-8 sequences follow of bit "patterns" (Table 3-6.) The
 * first byte determines the length of the sequence and then the next 0-3 bytes
 * are "continuation bytes."
 *
 * +----------------------------+----------+----------+----------+----------+
 * | Scalar Value               | 1st Byte | 2nd Byte | 3rd Byte | 4th Byte |
 * +----------------------------+----------+----------+----------+----------+
 * | 00000000 0xxxxxxx          | 0xxxxxxx |          |          |          |
 * | 00000yyy yyxxxxxx          | 110yyyyy | 10xxxxxx |          |          |
 * | zzzzyyyy yyxxxxxx          | 1110zzzz | 10yyyyyy | 10xxxxxx |          |
 * | 000uuuuu zzzzyyyy yyxxxxxx | 11110uuu | 10uuzzzz | 10yyyyyy | 10xxxxxx |
 * +----------------------------+----------+----------+----------+----------+
 *
 *      Table 3-6 from Unicode Standard 15.0.0 Ch3. UTF-8 bit patterns
 *
 * There are 3 further restrictions which make some valid bit patterns
 * *invalid*:
 *  1. Overlongs: eg, <0x41> and <0xC1 0x81> both store U+41, but the second
 *     sequence is longer and thus an error.
 *  2. Surrogates: Any codepoint between U+D800 and U+DFFF (inclusive) is a
 *     surrogate. It is an error to encode surrogates in UTF-8.
 *  3. Too Large: Any decoded value over 0x10FFFF is not a Unicode codepoint,
 *     and must be rejected as an error.
 *
 * See https://aolsen.ca/writings/everything-about-utf8 for more details about
 * the encoding.
 */

typedef enum Utf8Error {
  UTF8_OK = 0,

  // Encodes a codepoint in more bytes than necessary
  UTF8_ERR_OVERLONG = 1,

  // Encodes a codepoint in the surrogate range (0xD800 to 0xDFFF, inclusive)
  UTF8_ERR_SURROGATE = 2,

  // Encodes a value greater than the max codepoint U+10FFFF
  UTF8_ERR_TOO_LARGE = 3,

  // Encoding doesn't conform to the UTF-8 bit patterns
  UTF8_ERR_BAD_ENCODING = 4,

  // It looks like there is another codepoint, but it has been truncated.
  UTF8_ERR_TRUNCATED_BYTES = 5,
} Utf8Error_t;

typedef struct Utf8Result {
  Utf8Error_t error;
  uint32_t codepoint;
  size_t bytes_read;
} Utf8Result_t;

static inline void _cont(const unsigned char *input, Utf8Result_t *result) {
  if (result->error) return;

  int byte = input[result->bytes_read];
  if (byte == '\0') {
    result->error = UTF8_ERR_TRUNCATED_BYTES;
    return;
  }
  result->bytes_read += 1;

  // Continuation bytes follow the bit pattern 10xx_xxxx. We need to a)
  // validate the pattern and b) remove the leading '10'.
  if ((byte & 0xC0) == 0x80) {
    result->codepoint <<= 6;
    result->codepoint |= byte & 0x3F;
  } else {
    result->error = UTF8_ERR_BAD_ENCODING;
  }
}

/**
 * Given a nul-terminated string `input`, try to decode the next codepoint from
 * that string.
 *
 * It is required that `input` does not point to the nul-terminator. If
 * `*input == '\0'`, then it is assumed that the zero-byte is meant to encode
 * U+00, not a sentinel. The nul-terminator is still necessary because we need
 * it to prevent buffer overrun in the case of a truncated byte sequence, for
 * example '\xC2'. This oddity is to facilitate strings which may contain U+00
 * codepoints.
 *
 * If there was a surrogate, overlong or codepoint to large error then
 * `result.codepoint` will contain the recovered value.
 */
static inline void utf8_decode(const unsigned char *input,
                               Utf8Result_t *result) {
  result->error = UTF8_OK;
  result->codepoint = 0;
  result->bytes_read = 0;

  int first = *input;
  result->bytes_read = 1;

  if ((first & 0x80) == 0) {
    // 1-byte long (ASCII subset)
    result->codepoint = first;
    return;
  }

  if ((first & 0xE0) == 0xC0) {
    // 2-bytes long
    result->codepoint = first & 0x1F;

    _cont(input, result);
    if (result->error) return;

    if (result->codepoint < 0x80) {
      result->error = UTF8_ERR_OVERLONG;
    }

    return;
  }

  if ((first & 0xF0) == 0xE0) {
    // 3-bytes long
    result->codepoint = first & 0x0F;

    _cont(input, result);
    _cont(input, result);
    if (result->error) return;

    if (result->codepoint < 0x800) {
      result->error = UTF8_ERR_OVERLONG;
    }

    if (0xD800 <= result->codepoint && result->codepoint <= 0xDFFF) {
      result->error = UTF8_ERR_SURROGATE;
    }

    return;
  }

  if ((first & 0xF8) == 0xF0) {
    // 4-bytes long
    result->codepoint = first & 0x07;

    _cont(input, result);
    _cont(input, result);
    _cont(input, result);
    if (result->error) return;

    if (result->codepoint < 0x10000) {
      result->error = UTF8_ERR_OVERLONG;
    }

    if (result->codepoint > 0x10FFFF) {
      result->error = UTF8_ERR_TOO_LARGE;
    }

    return;
  }

  result->error = UTF8_ERR_BAD_ENCODING;
  return;
}

#endif  // DATA_LANG_UTF8_H
