#include "cpp/pylib.h"

#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST os_path_test() {
  // TODO: use gc_mylib here, with NewStr(), StackRoots, etc.
  BigStr* s = nullptr;

  s = os_path::rstrip_slashes(StrFromC(""));
  ASSERT(str_equals(s, StrFromC("")));

  s = os_path::rstrip_slashes(StrFromC("foo"));
  ASSERT(str_equals(s, StrFromC("foo")));

  s = os_path::rstrip_slashes(StrFromC("foo/"));
  ASSERT(str_equals(s, StrFromC("foo")));

  s = os_path::rstrip_slashes(StrFromC("/foo/"));
  ASSERT(str_equals(s, StrFromC("/foo")));

  // special case of not stripping
  s = os_path::rstrip_slashes(StrFromC("///"));
  ASSERT(str_equals(s, StrFromC("///")));

  ASSERT(path_stat::exists(StrFromC("/")));
  ASSERT(path_stat::exists(StrFromC("/usr/bin/sh")));
  ASSERT(!path_stat::exists(StrFromC("/nonexistent_ZZZ")));

  PASS();
}

TEST isdir_test() {
  ASSERT(path_stat::isdir(StrFromC(".")));
  ASSERT(path_stat::isdir(StrFromC("/")));
  ASSERT(!path_stat::isdir(StrFromC("/usr/bin/sh")));
  ASSERT(!path_stat::isdir(StrFromC("/nonexistent_ZZZ")));

  PASS();
}

TEST isfile_test() {
  ASSERT(!path_stat::isfile(StrFromC(".")));
  ASSERT(!path_stat::isfile(StrFromC("/")));
  ASSERT(path_stat::isfile(StrFromC("/usr/bin/sh")));
  ASSERT(!path_stat::isfile(StrFromC("/nonexistent_ZZZ")));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(os_path_test);
  RUN_TEST(isdir_test);
  RUN_TEST(isfile_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
