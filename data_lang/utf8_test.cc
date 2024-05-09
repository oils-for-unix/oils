#include <inttypes.h>

#include "data_lang/utf8.h"

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

TEST identity_test() {
  // check that decode(encode(x)) = x for all code-points (and surrogates)
  uint8_t buf[5] = {0};
  for (uint32_t cp = 1; cp < 0x10FFFF; ++cp) {
    int len = utf8proc_encode_char(cp, buf);
    Utf8Result result;
    utf8_decode(buf, &result);

    if (cp < 0xD800 || cp > 0xDFFF) {
      ASSERT_EQ(result.error, UTF8_OK);
    } else {
      ASSERT_EQ(result.error, UTF8_ERR_SURROGATE);
    }
    ASSERT_EQ(result.codepoint, cp);
    ASSERT_EQ(result.bytes_read, static_cast<size_t>(len));
  }

  PASS();
}

TEST overlong_test() {
  // All encode U+41 ('A')
  Utf8Result ok, overlong2, overlong3, overlong4;
  utf8_decode((unsigned char*)"\x41", &ok);
  utf8_decode((unsigned char*)"\xC1\x81", &overlong2);
  utf8_decode((unsigned char*)"\xE0\x81\x81", &overlong3);
  utf8_decode((unsigned char*)"\xF0\x80\x81\x81", &overlong4);

  ASSERT_EQ(ok.error, UTF8_OK);
  ASSERT_EQ(overlong2.error, UTF8_ERR_OVERLONG);
  ASSERT_EQ(overlong3.error, UTF8_ERR_OVERLONG);
  ASSERT_EQ(overlong4.error, UTF8_ERR_OVERLONG);

  ASSERT_EQ(ok.codepoint, 0x41);
  ASSERT_EQ(overlong2.codepoint, 0x41);
  ASSERT_EQ(overlong3.codepoint, 0x41);
  ASSERT_EQ(overlong4.codepoint, 0x41);

  ASSERT_EQ(ok.bytes_read, 1);
  ASSERT_EQ(overlong2.bytes_read, 2);
  ASSERT_EQ(overlong3.bytes_read, 3);
  ASSERT_EQ(overlong4.bytes_read, 4);

  PASS();
}

TEST too_large_test() {
  // Encoding of 0x111111 (via Table 3-6)
  //  = 00010001 00010001 00010001
  //   uuuuu -> 10001
  //    zzzz -> 00001
  //  yyyyyy -> 000100
  //  xxxxxx -> 010001
  //
  //  -> 11110100 10010001 10000100 10010001
  //   = F4 91 84 91
  Utf8Result result;
  utf8_decode((unsigned char*)"\xF4\x91\x84\x91", &result);

  ASSERT_EQ(result.error, UTF8_ERR_TOO_LARGE);
  ASSERT_EQ(result.codepoint, 0x111111);
  ASSERT_EQ(result.bytes_read, 4);

  PASS();
}

TEST truncated_test() {
  Utf8Result result;

  constexpr const int NUM_INPUTS = 6;
  const char *inputs[NUM_INPUTS] = {
    "\xC5",
    "\xED",
    "\xED\x9F",
    "\xF4",
    "\xF4\x80",
    "\xF4\x80\x80",
  };

  for (int i = 0; i < NUM_INPUTS; i++) {
    utf8_decode((unsigned char*)inputs[i], &result);
    ASSERT_EQ(result.error, UTF8_ERR_TRUNCATED_BYTES);
    ASSERT_EQ(result.bytes_read, strlen(inputs[i]));
  }

  // End of stream is separate from truncated
  utf8_decode((unsigned char*)"", &result);
  ASSERT_EQ(result.error, UTF8_ERR_END_OF_STREAM);
  ASSERT_EQ(result.bytes_read, 0);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  GREATEST_MAIN_BEGIN();

  RUN_TEST(identity_test);
  RUN_TEST(overlong_test);
  RUN_TEST(too_large_test);
  RUN_TEST(truncated_test);

  GREATEST_MAIN_END();
  return 0;
}
