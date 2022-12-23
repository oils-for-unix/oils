#include "cpp/stdlib.h"

#include <errno.h>

#include "mycpp/gc_builtins.h"
#include "vendor/greatest.h"

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

TEST open_test() {
  bool caught = false;
  try {
    posix::open(StrFromC("nonexistent_ZZ"), 0, 0);
  } catch (IOError_OSError* e) {
    caught = true;
  }
  ASSERT(caught);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(time_test);
  RUN_TEST(posix_test);
  RUN_TEST(putenv_test);
  RUN_TEST(open_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
