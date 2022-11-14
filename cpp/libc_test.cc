#include "cpp/libc.h"

#include <unistd.h>  // gethostname()

#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST hostname_test() {
  Str* s0 = libc::gethostname();
  ASSERT(s0 != nullptr);

  char buf[1024];
  ASSERT(gethostname(buf, HOST_NAME_MAX) == 0);
  ASSERT(str_equals(s0, StrFromC(buf)));

  PASS();
}

TEST libc_test() {
  Str* s1 = (StrFromC("foo.py "))->strip();
  ASSERT(libc::fnmatch(StrFromC("*.py"), s1));
  ASSERT(!libc::fnmatch(StrFromC("*.py"), StrFromC("foo.p")));

  // extended glob
  ASSERT(libc::fnmatch(StrFromC("*(foo|bar).py"), StrFromC("foo.py")));
  ASSERT(!libc::fnmatch(StrFromC("*(foo|bar).py"), StrFromC("foo.p")));

  List<Str*>* results =
      libc::regex_match(StrFromC("(a+).(a+)"), StrFromC("-abaacaaa"));
  ASSERT_EQ_FMT(3, len(results), "%d");
  ASSERT(str_equals(StrFromC("abaa"), results->index_(0)));  // whole match
  ASSERT(str_equals(StrFromC("a"), results->index_(1)));
  ASSERT(str_equals(StrFromC("aa"), results->index_(2)));

  results = libc::regex_match(StrFromC("z+"), StrFromC("abaacaaa"));
  ASSERT_EQ(nullptr, results);

  Tuple2<int, int>* result;
  Str* s = StrFromC("oXooXoooXoX");
  result = libc::regex_first_group_match(StrFromC("(X.)"), s, 0);
  ASSERT_EQ_FMT(1, result->at0(), "%d");
  ASSERT_EQ_FMT(3, result->at1(), "%d");

  result = libc::regex_first_group_match(StrFromC("(X.)"), s, 3);
  ASSERT_EQ_FMT(4, result->at0(), "%d");
  ASSERT_EQ_FMT(6, result->at1(), "%d");

  result = libc::regex_first_group_match(StrFromC("(X.)"), s, 6);
  ASSERT_EQ_FMT(8, result->at0(), "%d");
  ASSERT_EQ_FMT(10, result->at1(), "%d");

  Str* h = libc::gethostname();
  log("gethostname() = %s %d", h->data_, len(h));

  PASS();
}

TEST libc_glob_test() {
  // This depends on the file system
  auto files = libc::glob(StrFromC("*.testdata"));
  // 3 files are made by the shell wrapper
  ASSERT_EQ_FMT(3, len(files), "%d");

  print(files->index_(0));

  auto files2 = libc::glob(StrFromC("*.pyzzz"));
  ASSERT_EQ_FMT(0, len(files2), "%d");

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(libc_test);
  RUN_TEST(libc_glob_test);
  RUN_TEST(hostname_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
