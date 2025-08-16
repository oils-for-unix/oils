#include "cpp/libc.h"

#include <locale.h>  // setlocale()
#include <regex.h>   // regcomp()
#include <unistd.h>  // gethostname()

#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST hostname_test() {
  BigStr* s0 = libc::gethostname();
  ASSERT(s0 != nullptr);

  char buf[1024];
  ASSERT(gethostname(buf, HOST_NAME_MAX) == 0);
  ASSERT(str_equals(s0, StrFromC(buf)));

  PASS();
}

TEST realpath_test() {
  BigStr* result = libc::realpath(StrFromC("/"));
  ASSERT(str_equals(StrFromC("/"), result));

  bool caught = false;
  try {
    libc::realpath(StrFromC("/nonexistent_ZZZ"));
  } catch (IOError_OSError* e) {
    caught = true;
  }
  ASSERT(caught);

  PASS();
}

TEST libc_test() {
  log("sizeof(wchar_t) = %d", sizeof(wchar_t));

  int width = 0;

  // TODO: enable this test.  Is it not picking LC_CTYPE?
  // Do we have to do some initialization like libc.cpython_reset_locale() ?
#if 0
  try {
    // mu character \u{03bc} in utf-8
    width = libc::wcswidth(StrFromC("\xce\xbc"));
  } catch (UnicodeError* e) {
    log("UnicodeError %s", e->message->data_);
  }
  ASSERT_EQ_FMT(2, width, "%d");
#endif

  BigStr* h = libc::gethostname();
  log("gethostname() = %s %d", h->data_, len(h));

  width = libc::wcswidth(StrFromC("foo"));
  ASSERT_EQ(3, width);

  libc::print_time(0.1, 0.2, 0.3);

  PASS();
}

static List<BigStr*>* Groups(BigStr* s, List<int>* indices) {
  List<BigStr*>* groups = NewList<BigStr*>();
  int n = len(indices) / 2;
  for (int i = 0; i < n; ++i) {
    int start = indices->at(2 * i);
    int end = indices->at(2 * i + 1);
    if (start == -1) {
      groups->append(nullptr);
    } else {
      groups->append(s->slice(start, end));
    }
  }
  return groups;
}

TEST regex_wrapper_test() {
  BigStr* s1 = StrFromC("-abaacaaa");
  List<int>* indices = libc::regex_search(StrFromC("(a+).(a+)"), 0, s1, 0);
  List<BigStr*>* results = Groups(s1, indices);
  ASSERT_EQ_FMT(3, len(results), "%d");
  ASSERT(str_equals(StrFromC("abaa"), results->at(0)));  // whole match
  ASSERT(str_equals(StrFromC("a"), results->at(1)));
  ASSERT(str_equals(StrFromC("aa"), results->at(2)));

  indices = libc::regex_search(StrFromC("z+"), 0, StrFromC("abaacaaa"), 0);
  ASSERT_EQ(nullptr, indices);

  // Alternation gives unmatched group
  BigStr* s2 = StrFromC("b");
  indices = libc::regex_search(StrFromC("(a)|(b)"), 0, s2, 0);
  results = Groups(s2, indices);
  ASSERT_EQ_FMT(3, len(results), "%d");
  ASSERT(str_equals(StrFromC("b"), results->at(0)));  // whole match
  ASSERT_EQ(nullptr, results->at(1));
  ASSERT(str_equals(StrFromC("b"), results->at(2)));

  // Like Unicode test below
  indices = libc::regex_search(StrFromC("_._"), 0, StrFromC("_x_"), 0);
  ASSERT(indices != nullptr);
  ASSERT_EQ_FMT(2, len(indices), "%d");
  ASSERT_EQ_FMT(0, indices->at(0), "%d");
  ASSERT_EQ_FMT(3, indices->at(1), "%d");

  // TODO(unicode)
#if 0
  //indices = libc::regex_search(StrFromC("_._"), 0, StrFromC("_\u03bc_"), 0);
  indices = libc::regex_search(StrFromC("_._"), 0, StrFromC("_μ_"), 0);
  ASSERT(indices != nullptr);
  ASSERT_EQ_FMT(2, len(indices), "%d");
  ASSERT_EQ_FMT(0, indices->at(0), "%d");
  ASSERT_EQ_FMT(0, indices->at(0), "%d");
#endif

  Tuple2<int, int>* result;
  BigStr* s = StrFromC("oXooXoooXoX");
  result = libc::regex_first_group_match(StrFromC("(X.)"), s, 0);
  ASSERT_EQ_FMT(1, result->at0(), "%d");
  ASSERT_EQ_FMT(3, result->at1(), "%d");

  result = libc::regex_first_group_match(StrFromC("(X.)"), s, 3);
  ASSERT_EQ_FMT(4, result->at0(), "%d");
  ASSERT_EQ_FMT(6, result->at1(), "%d");

  result = libc::regex_first_group_match(StrFromC("(X.)"), s, 6);
  ASSERT_EQ_FMT(8, result->at0(), "%d");
  ASSERT_EQ_FMT(10, result->at1(), "%d");

  PASS();
}

TEST glob_test() {
  // This depends on the file system
  auto files = libc::glob(StrFromC("*.testdata"));
  // 3 files are made by the shell wrapper
  ASSERT_EQ_FMT(3, len(files), "%d");

  print(files->at(0));

  auto files2 = libc::glob(StrFromC("*.pyzzz"));
  ASSERT_EQ_FMT(0, len(files2), "%d");

  PASS();
}

TEST fnmatch_test() {
  BigStr* s1 = (StrFromC("foo.py "))->strip();
  ASSERT(libc::fnmatch(StrFromC("*.py"), s1));
  ASSERT(!libc::fnmatch(StrFromC("*.py"), StrFromC("foo.p")));

  // Unicode - ? is byte or code point?
  ASSERT(libc::fnmatch(StrFromC("_?_"), StrFromC("_x_")));

  // TODO(unicode)
  // ASSERT(libc::fnmatch(StrFromC("_?_"), StrFromC("_\u03bc_")));
  // ASSERT(libc::fnmatch(StrFromC("_?_"), StrFromC("_μ_")));

  // extended glob
  ASSERT(libc::fnmatch(StrFromC("*(foo|bar).py"), StrFromC("foo.py")));
  ASSERT(!libc::fnmatch(StrFromC("*(foo|bar).py"), StrFromC("foo.p")));

  PASS();
}

TEST for_test_coverage() {
  // Sometimes we're not connected to a terminal
  try {
    libc::get_terminal_width();
  } catch (IOError_OSError* e) {
  }

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(hostname_test);
  RUN_TEST(realpath_test);
  RUN_TEST(libc_test);
  RUN_TEST(regex_wrapper_test);
  RUN_TEST(glob_test);
  RUN_TEST(fnmatch_test);
  RUN_TEST(for_test_coverage);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
