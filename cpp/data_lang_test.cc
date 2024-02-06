#include "cpp/data_lang.h"

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

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(PartIsUtf8_test);
  RUN_TEST(WriteString_test);
  RUN_TEST(compare_c_test);
  RUN_TEST(heap_id_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
