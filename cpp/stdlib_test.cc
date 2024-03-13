#include "cpp/stdlib.h"

#include <errno.h>
#include <sys/stat.h>

#include "mycpp/gc_builtins.h"
#include "vendor/greatest.h"

TEST posix_test() {
  ASSERT_EQ(false, posix::access(StrFromC("nonexistent_ZZ"), R_OK));

  BigStr* cwd = posix::getcwd();
  log("getcwd() = %s %d", cwd->data_, len(cwd));

  ASSERT(posix::getegid() > 0);
  ASSERT(posix::geteuid() > 0);
  ASSERT(posix::getpid() > 0);
  ASSERT(posix::getppid() > 0);
  ASSERT(posix::getuid() > 0);

  int pgid = posix::getpgid(0);
  log("pgid = %d", pgid);

  // pgid = posix::getpgid(9999);
  // log("pgid = %d", pgid);

  Tuple2<int, int> fds = posix::pipe();
  ASSERT(fds.at0() > 0);
  ASSERT(fds.at1() > 0);

  ASSERT_EQ(false, posix::isatty(fds.at0()));

  posix::close(fds.at0());

  BigStr* message = posix::strerror(EBADF);
  log("strerror");
  print(message);

  PASS();
}

TEST putenv_test() {
  BigStr* key = StrFromC("KEY");
  BigStr* value = StrFromC("value");

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

  // Can open a directory
  int fd = posix::open(StrFromC("."), 0, 0666);
  ASSERT(fd > 0);

  PASS();
}

TEST time_test() {
  int ts = time_::time();
  log("ts = %d", ts);
  ASSERT(ts > 0);

  BigStr* s = time_::strftime(StrFromC("%Y-%m-%d"), ts);
  print(s);

  ASSERT(len(s) > 5);

  PASS();
}

// To figure out how we should use stat() for core/completion.py
// The number of seconds should suffice, for another 15 years :-P
TEST mtime_demo() {
  struct stat statbuf;
  if (stat("README.md", &statbuf) < 0) {
    ASSERT(false);
  }

  // POSIX API
  long mtime = statbuf.st_mtime;
  log("mtime        = %10ld", mtime);

  // More precision
  long secs = statbuf.st_mtim.tv_sec;
  log("mtim.tv_sec  = %10ld", secs);

  long ns = statbuf.st_mtim.tv_nsec;
  log("mtim.tv_nsec = %10ld", ns);

  BigStr* s = time_::strftime(StrFromC("%Y-%m-%d"), secs);
  print(s);

  log("INT_MAX      = %10d", INT_MAX);
  log("diff         = %10d", INT_MAX - statbuf.st_mtime);

  s = time_::strftime(StrFromC("%Y-%m-%d"), INT_MAX);
  print(s);

  PASS();
}

TEST listdir_test() {
  List<BigStr*>* contents = posix::listdir(StrFromC("/"));
  // This should be universally true on any working Unix right...?
  ASSERT(len(contents) > 0);

  int ec = -1;
  try {
    posix::listdir(StrFromC("nonexistent_ZZ"));
  } catch (IOError_OSError* e) {
    ec = e->errno_;
  }
  ASSERT(ec == ENOENT);

  PASS();
}

TEST for_test_coverage() {
  time_::sleep(0);

  // I guess this has side effects
  time_::tzset();

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
  RUN_TEST(mtime_demo);
  RUN_TEST(listdir_test);

  RUN_TEST(for_test_coverage);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
