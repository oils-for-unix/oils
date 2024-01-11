#include "cpp/data_lang.h"

#include "data_lang/j8_test_lib.h"
#include "data_lang/j8c.h"  // for comparison
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
    j8_buf_t in = {(unsigned char*)s, strlen(s)};

    j8_buf_t c_result = {0};
    J8EncodeString(in, &c_result, 0);

    printf("c_result %s\n", c_result.data);
    printf("c_result.len %d\n", c_result.len);

#if 0
    BigStr* s2 = StrFromC(s);

    buf = Alloc<mylib::BufWriter>();
    pyj8::WriteString(s2, LOSSY_JSON, buf);

    BigStr* cpp_result = buf->getvalue();
    ASSERT_EQ_FMT(c_result.len, len(cpp_result), "%d");
#endif

    free(c_result.data);

#if 0
    // Encode again with J8 fallback
    c_result = {0};
    J8EncodeString(in, &c_result, 1);

    printf("c_result %s\n", c_result.data);
    printf("c_result.len %d\n", c_result.len);
    free(c_result.data);
#endif

    printf("\n");
  }

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(PartIsUtf8_test);
  RUN_TEST(WriteString_test);
  RUN_TEST(compare_c_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
