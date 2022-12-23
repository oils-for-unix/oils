#include "cpp/stdlib.h"

#include <errno.h>

#include "mycpp/gc_builtins.h"
#include "vendor/greatest.h"

TEST posix_test() {
  ASSERT_EQ(false, posix::access(StrFromC("nonexistent_ZZ"), R_OK));

  Str* cwd = posix::getcwd();
  log("getcwd() = %s %d", cwd->data_, len(cwd));

  ASSERT(posix::getegid() > 0);
  ASSERT(posix::geteuid() > 0);
  ASSERT(posix::getpid() > 0);
  ASSERT(posix::getppid() > 0);
  ASSERT(posix::getuid() > 0);

  Tuple2<int, int> fds = posix::pipe();
  ASSERT(fds.at0() > 0);
  ASSERT(fds.at1() > 0);

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

TEST time_test() {
  int ts = time_::time();
  log("ts = %d", ts);
  ASSERT(ts > 0);

  Str* s = time_::strftime(StrFromC("%Y-%m-%d"), ts);
  print(s);

  ASSERT(len(s) > 5);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(posix_test);
  RUN_TEST(putenv_test);
  RUN_TEST(open_test);
  RUN_TEST(time_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
