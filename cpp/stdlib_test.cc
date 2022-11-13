
#include "cpp/stdlib.h"

#include <errno.h>

#include "_gen/core/runtime.asdl.h"  // cell, etc
#include "cpp/core_error.h"          // FatalRuntime
#include "cpp/pylib.h"
#include "mycpp/gc_builtins.h"
#include "vendor/greatest.h"

TEST show_sizeof() {
  // Without sed hack, it's 24 bytes because we have tag (2), id (4), val,
  // span_id.
  // Now 16 bytes.
  log("sizeof(Token) = %d", sizeof(syntax_asdl::Token));
  log("alignof(Token) = %d", alignof(syntax_asdl::Token));
  log("alignof(Token*) = %d", alignof(syntax_asdl::Token*));

  // Without sed hack, it's 12 bytes for tag (2) id (4) and span_id (4).
  // Now 8 bytes.
  log("sizeof(speck) = %d", sizeof(syntax_asdl::speck));

  // 16 bytes: 2 byte tag + 3 integer fields
  log("sizeof(line_span) = %d", sizeof(syntax_asdl::line_span));

  // Reordered to be 16 bytes
  log("sizeof(cell) = %d", sizeof(runtime_asdl::cell));

  // 24 bytes: std::vector
  log("sizeof(List<int>) = %d", sizeof(List<int>));
  log("sizeof(List<Str*>) = %d", sizeof(List<Str*>));

  // Unlike Python, this is -1, not 255!
  int mod = -1 % 256;
  log("mod = %d", mod);

  log("alignof(bool) = %d", alignof(bool));
  log("alignof(int) = %d", alignof(int));
  log("alignof(float) = %d", alignof(float));

  log("sizeof(Str) = %d", sizeof(Str));
  log("alignof(Str) = %d", alignof(Str));

  log("sizeof(Str*) = %d", sizeof(Str*));
  log("alignof(Str*) = %d", alignof(Str*));

  log("alignof(max_align_t) = %d", alignof(max_align_t));

  PASS();
}

TEST time_test() {
  int ts = time_::time();
  log("ts = %d", ts);
  ASSERT(ts > 0);
  PASS();
}

TEST posix_test() {
  Str* cwd = posix::getcwd();
  log("getcwd() = %s %d", cwd->data_, len(cwd));

  Str* message = posix::strerror(EBADF);
  log("strerror");
  print(message);

  PASS();
}

TEST putenv_test() {
  Str* key = StrFromC("KEY");
  Str* value = StrFromC("value");

  posix::putenv(key, value);
  char* got_value = ::getenv(key->data());
  ASSERT(got_value && str_equals(StrFromC(got_value), value));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(show_sizeof);
  RUN_TEST(time_test);
  RUN_TEST(posix_test);
  RUN_TEST(putenv_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
