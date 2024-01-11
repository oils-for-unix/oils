#include "cpp/data_lang.h"

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
  pyj8::WriteString(kEmptyString, 0, buf);

  BigStr* result = buf->getvalue();
  log("result = %s", result->data_);

  buf = Alloc<mylib::BufWriter>();
  pyj8::WriteString(kEmptyString, LOSSY_JSON, buf);

  result = buf->getvalue();
  log("result = %s", result->data_);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  GREATEST_MAIN_BEGIN();

  RUN_TEST(PartIsUtf8_test);
  RUN_TEST(WriteString_test);

  GREATEST_MAIN_END();
  return 0;
}
