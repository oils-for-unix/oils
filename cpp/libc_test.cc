#include "cpp/libc.h"

#include <locale.h>  // setlocale()
#include <regex.h>   // regcomp()
#include <unistd.h>  // gethostname()
#include <wctype.h>  // towupper()

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

void FindAll(const char* p, const char* s) {
  regex_t pat;

  int cflags = REG_EXTENDED;
  if (regcomp(&pat, p, cflags) != 0) {
    FAIL();
  }
  int outlen = pat.re_nsub + 1;  // number of captures

  // TODO: Could statically allocate 99, and assert that re_nsub is less than
  // 99.  Would speed up loops.
  regmatch_t* pmatch =
      static_cast<regmatch_t*>(malloc(sizeof(regmatch_t) * outlen));

  int cur_pos = 0;
  // int n = strlen(s);
  while (true) {
    // Necessary so ^ doesn't match in the middle!
    int eflags = cur_pos == 0 ? 0 : REG_NOTBOL;
    bool match = regexec(&pat, s + cur_pos, outlen, pmatch, eflags) == 0;

    if (!match) {
      break;
    }
    int i;
    for (i = 0; i < outlen; i++) {
      int start = pmatch[i].rm_so;
      int end = pmatch[i].rm_eo;
      int len = end - start;
      BigStr* m = StrFromC(s + cur_pos + start, len);
      log("%d GROUP %d (%d .. %d) = [%s]", cur_pos, i, start, end, m->data_);
    }
    log("");
    int match_len = pmatch[0].rm_eo;
    if (match_len == 0) {
      break;
    }
    cur_pos += match_len;
  }

  free(pmatch);
  regfree(&pat);
}

// adjacent matches
const char* s = "a345y-axy- there b789y- cy-";

TEST regex_unanchored() {
  const char* unanchored = "[abc]([0-9]*)(x?)(y)-";
  FindAll(unanchored, s);

  PASS();
}

TEST regex_caret() {
  const char* anchored = "^[abc]([0-9]*)(x?)(y)-";
  FindAll(anchored, s);

  PASS();
}

TEST regex_lexer() {
  // like the Yaks / Make-a-Lisp pattern
  const char* lexer = "([a-z]+)|([0-9]+)|([ ]+)|([+-])";
  FindAll(lexer, s);

  PASS();
}

TEST regex_repeat_with_capture() {
  const char* lexer = "(([a-z]+)([0-9]+)-)*((A+)|(Z+))*";
  FindAll(lexer, "a0-b1-c2-AAZZZA");
  // Groups are weird
  // whole match 0: a0-b1-c2-
  //             1: c2-      # last repetition
  //             2: c        # last one
  //             3: 2        # last one
  //
  // And then there's an empty match
  //
  // Ideas:
  // - disallow nested groups in Eggex?
  // - I really care about the inner ones -- groups 2 and 3
  // - I want flat groups

  PASS();
}

// Disallow this in eggex, as well as the above
TEST regex_nested_capture() {
  const char* lexer = "(([a-z]+)([0-9]+))";
  FindAll(lexer, "a0");
  PASS();
}

// I think we allow this in eggex
TEST regex_alt_with_capture() {
  const char* lexer = "([a-z]+)|([0-9]+)(-)";
  FindAll(lexer, "x-");
  FindAll(lexer, "7-");
  PASS();
}

TEST regex_unicode() {
  regex_t pat;

  // 1 or 2 bytes
  // const char* p = "_..?_";
  // const char* p = "_[^a]_";
  const char* p = "_._";  // 1 byte, not code point?

  if (regcomp(&pat, p, REG_EXTENDED) != 0) {
    FAIL();
  }
  int outlen = pat.re_nsub + 1;  // number of captures
  regmatch_t* pmatch =
      static_cast<regmatch_t*>(malloc(sizeof(regmatch_t) * outlen));

  int result;

  const char* bad = "_xyz_";
  result = regexec(&pat, bad, outlen, pmatch, 0);
  ASSERT_EQ_FMT(1, result, "%d");  // does not match

  const char* a = "_x_";
  result = regexec(&pat, a, outlen, pmatch, 0);
  ASSERT_EQ_FMT(0, result, "%d");

  // Doesn't change anything
  // int lc_what = LC_ALL;
  int lc_what = LC_CTYPE;

  // char* saved_locale = setlocale(LC_ALL, "");
  // char* saved_locale = setlocale(LC_ALL, NULL);

  // char* saved_locale = setlocale(lc_what, NULL);

#if 0
  // Doesn't change anything?
  //if (setlocale(LC_CTYPE, "C.utf8") == NULL) {
  if (setlocale(LC_CTYPE, "en_US.UTF-8") == NULL) {
    log("Couldn't set locale to C.utf8");
    FAIL();
  }
#endif

  // const char* u = "_μ_";
  const char* u = "_\u03bc_";
  log("a = %d bytes", strlen(a));
  log("u = %d bytes", strlen(u));
  result = regexec(&pat, u, outlen, pmatch, 0);

#if 0
  if (setlocale(lc_what, saved_locale) == NULL) {
    log("Couldn't restore locale");
    FAIL();
  }
#endif

  free(pmatch);  // Clean up before test failures
  regfree(&pat);

  // TODO(unicode)
  // ASSERT_EQ_FMT(0, result, "%d");

  PASS();
}

TEST casefold_test() {
#if 0
  // Turkish
  if (setlocale(LC_CTYPE, "tr_TR.utf8") == NULL) {
    log("Couldn't set locale to tr_TR.utf8");
    FAIL();
  }
#endif

  // LC_CTYPE_MASK instead of LC_CTYPE
  locale_t turkish = newlocale(LC_CTYPE_MASK, "tr_TR.utf8", NULL);

  int u = toupper('i');
  int wu = towupper('i');
  int wul = towupper_l('i', turkish);

  // Regular: upper case i is I, 73
  // Turkish: upper case is 304
  log("upper = %d", u);
  log("wide upper = %d", wu);
  log("wide upper locale = %d", wul);

  freelocale(turkish);

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

  RUN_TEST(regex_unanchored);
  RUN_TEST(regex_caret);
  RUN_TEST(regex_lexer);
  RUN_TEST(regex_repeat_with_capture);
  RUN_TEST(regex_alt_with_capture);
  RUN_TEST(regex_nested_capture);
  RUN_TEST(regex_unicode);

  RUN_TEST(casefold_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
