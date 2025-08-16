#include <locale.h>  // setlocale()
#include <regex.h>   // regcomp()
#include <wctype.h>  // towupper()

#include "mycpp/runtime.h"
#include "vendor/greatest.h"

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
  // const char* u = "_\u03bc_";

  // utf-8 encoding
  const char* u = "_\xce\xbc_";

  log("a = %d bytes", strlen(a));
  log("u = %d bytes", strlen(u));
  result = regexec(&pat, u, outlen, pmatch, 0);

  // This doesn't match because of setlocale()
  // ASSERT_EQ_FMT(0, result, "%d");

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

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  // TODO: move to cpp/regex_demo.cc
  // and consolidate unicode too
  RUN_TEST(regex_unanchored);
  RUN_TEST(regex_caret);
  RUN_TEST(regex_lexer);
  RUN_TEST(regex_repeat_with_capture);
  RUN_TEST(regex_alt_with_capture);
  RUN_TEST(regex_nested_capture);
  RUN_TEST(regex_unicode);

  // Crashes in CI?  Because of Turkish locale?
  // RUN_TEST(casefold_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
