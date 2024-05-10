#include "cpp/data_lang.h"

#include <stdio.h>

#include "_gen/core/value.asdl.h"
#include "data_lang/j8_libc.h"  // for comparison
#include "data_lang/j8_test_lib.h"
#include "vendor/greatest.h"

TEST PartIsUtf8_test() {
  BigStr* s = StrFromC("hi");

  ASSERT(pyj8::PartIsUtf8(s, 0, 2));

  // empty string is trivially UTF-8
  ASSERT(pyj8::PartIsUtf8(s, 0, 0));

  BigStr* binary = StrFromC("h\xff");
  ASSERT(!pyj8::PartIsUtf8(binary, 0, len(binary)));

  // first byte is UTF-8
  ASSERT(pyj8::PartIsUtf8(binary, 0, 1));
  // second byte isn't
  ASSERT(!pyj8::PartIsUtf8(binary, 1, 2));

  PASS();
}

// TODO: remove duplication
#define LOSSY_JSON (1 << 3)

TEST WriteString_test() {
  auto buf = Alloc<mylib::BufWriter>();

  for (int i = 0; J8_TEST_CASES[i]; ++i) {
    const char* s = J8_TEST_CASES[i];
    BigStr* s2 = StrFromC(s);

    buf = Alloc<mylib::BufWriter>();
    pyj8::WriteString(s2, LOSSY_JSON, buf);

    BigStr* result = buf->getvalue();
    log("result = %s", result->data_);

    buf = Alloc<mylib::BufWriter>();
    pyj8::WriteString(s2, 0, buf);

    result = buf->getvalue();
    log("result = %s", result->data_);
  }

  PASS();
}

TEST compare_c_test() {
  // Compare two implementations

  auto buf = Alloc<mylib::BufWriter>();

  for (int i = 0; J8_TEST_CASES[i]; ++i) {
    const char* s = J8_TEST_CASES[i];
    int input_len = strlen(s);
    j8_buf_t in = {(unsigned char*)s, input_len};

    j8_buf_t c_result = {0};
    J8EncodeString(in, &c_result, 0);

    printf("c_result %s\n", c_result.data);
    printf("c_result.len %d\n", c_result.len);

    BigStr* s2 = StrFromC(s);

    buf = Alloc<mylib::BufWriter>();
    pyj8::WriteString(s2, LOSSY_JSON, buf);

    BigStr* cpp_result = buf->getvalue();

    // Equal lengths
    ASSERT_EQ_FMT(c_result.len, len(cpp_result), "%d");
    // Equal contents
    ASSERT(memcmp(c_result.data, cpp_result->data_, c_result.len) == 0);

    free(c_result.data);

    //
    // Encode again with J8 fallback
    //

    c_result = {0};
    J8EncodeString(in, &c_result, 1);

    printf("c_result %s\n", c_result.data);
    printf("c_result.len %d\n", c_result.len);

    buf = Alloc<mylib::BufWriter>();
    pyj8::WriteString(s2, 0, buf);

    cpp_result = buf->getvalue();

    // Equal lengths
    ASSERT_EQ_FMT(c_result.len, len(cpp_result), "%d");
    // Equal contents
    ASSERT(memcmp(c_result.data, cpp_result->data_, c_result.len) == 0);

    free(c_result.data);

    printf("\n");
  }

  PASS();
}

using value_asdl::value;
using value_asdl::value_t;

TEST heap_id_test() {
  value_t* val1 = Alloc<value::Str>(kEmptyString);
  value_t* val2 = Alloc<value::Str>(kEmptyString);

  int id1 = j8::HeapValueId(val1);
  int id2 = j8::HeapValueId(val2);

  log("id1 = %d, id2 = %d", id1, id2);
  ASSERT(id1 != id2);

  PASS();
}

TEST utf8_decode_one_test() {
#define ASSERT_DECODE(codepoint, bytes_read, string, start)               \
  do {                                                                    \
    Tuple2<int, int> result = fastfunc::Utf8DecodeOne((string), (start)); \
    ASSERT_EQ(result.at0(), (codepoint));                                 \
    ASSERT_EQ(result.at1(), (bytes_read));                                \
  } while (false)

  BigStr* s = StrFromC("h\xE2\xA1\x80\xC5\x81");
  ASSERT_DECODE('h', 1, s, 0);
  ASSERT_DECODE(0x2840, 3, s, 1);
  ASSERT_DECODE(0x141, 2, s, 4);

  // UTF8_ERR_END_OF_STREAM = 6
  ASSERT_DECODE(-6, 0, s, 6);

  // UTF8_ERR_OVERLONG = 1
  ASSERT_DECODE(-1, 2, StrFromC("\xC1\x81"), 0);

  // UTF8_ERR_SURROGATE = 2
  ASSERT_DECODE(-2, 3, StrFromC("\xED\xBF\x80"), 0);

  // UTF8_ERR_TOO_LARGE = 3
  ASSERT_DECODE(-3, 4, StrFromC("\xF4\xA0\x80\x80"), 0);

  // UTF8_ERR_BAD_ENCODING = 4
  ASSERT_DECODE(-4, 2, StrFromC("\xC2\xFF"), 0);

  // UTF8_ERR_TRUNCATED_BYTES = 5
  ASSERT_DECODE(-5, 1, StrFromC("\xC2"), 0);

  PASS();
#undef ASSERT_DECODE
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(PartIsUtf8_test);
  RUN_TEST(WriteString_test);
  RUN_TEST(compare_c_test);
  RUN_TEST(heap_id_test);
  RUN_TEST(utf8_decode_one_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
