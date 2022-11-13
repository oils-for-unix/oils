#include "cpp/pylib.h"

#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST os_path_test() {
  // TODO: use gc_mylib here, with NewStr(), StackRoots, etc.
  Str* s = nullptr;

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

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(os_path_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
