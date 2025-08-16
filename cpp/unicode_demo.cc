#include <locale.h>
#include <regex.h>

#include "mycpp/common.h"
#include "vendor/greatest.h"

TEST libc_demo() {
  int x = strcmp("a", "b");
  log("strcmp = %d", x);
  x = strcmp("a", "a");
  log("strcmp = %d", x);

  // Functions to test with:
  // - different LANG settings
  // - musl libc vs. GNU libc, etc.
  //
  // glob() and fnmatch()
  // regexec()
  // strcoll()
  // int toupper(), tolower(), toupper_l() can be passed locale
  //
  // See doc/unicode.md

  // We could have pyext/libc.c wrappers for this, rather than using Python
  // str.upper().  Maybe remove Str::{upper,lower}() from the Yaks language,
  // since it depends on Unicode.

  int c;
  c = toupper((unsigned char)'a');
  log("toupper %c", c);

  c = tolower((unsigned char)c);
  log("tolower %c", c);
}

// Note: libc_trest.cc regex_unicode() also tests this
TEST regex_demo() {
  // From Claude: Set locale to handle UTF-8
  // Oh does GNU readline set this ?!?  Yes that's what's going on!  Geez
  // Then do we have a bug without GNU readline?
  // TODO: test  it
  setlocale(LC_ALL, "");

#if 1
  const char* regex = ".";
  // mu character
  const char* s = "\xce\xbc";
#endif
#if 0
  const char* regex = "[\xce\xbc]";
  const char* s = "\xce\xbc";
#endif
#if 0
  const char* regex = "[b]";
  const char* s = "abc";
#endif

  regex_t pat;
  int status = regcomp(&pat, regex, REG_EXTENDED);
  if (status != 0) {
    FAIL();
  }

  int num_groups = pat.re_nsub + 1;  // number of captures

  regmatch_t* pmatch =
      static_cast<regmatch_t*>(malloc(sizeof(regmatch_t) * num_groups));
  int eflags = 0;
  bool match = regexec(&pat, s, num_groups, pmatch, eflags) == 0;
  if (match) {
    printf("match\n");
    for (int i = 0; i < num_groups; i++) {
      int start = pmatch[i].rm_so;
      int end = pmatch[i].rm_eo;
      printf("start %d - %d\n", start, end);
    }
  }
  free(pmatch);
  regfree(&pat);

  PASS();
}

TEST isspace_demo() {
  int x;

  // 0xa0 from
  // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Lexical_grammar#white_space
  //
  // Somehow it's false
  //
  // In Python we have
  // >>> '\u00a0'.isspace()
  // True

  // U+00A0 is non-breaking space
  // U+FEFF is zero-width no break space - this is true
  int cases[] = {'\0', '\t', '\v', '\f', ' ', 'a', 0xa0, 0xfeff};
  int n = sizeof(cases) / sizeof(cases[0]);

  for (int i = 0; i < n; ++i) {
    int x = isspace(cases[i]);
    log("isspace %x %d", cases[i], x);
  }
  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  // gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(libc_demo);
  RUN_TEST(isspace_demo);
  RUN_TEST(regex_demo);

  // gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
