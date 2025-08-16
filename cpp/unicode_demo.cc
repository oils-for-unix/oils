#include <locale.h>
#include <regex.h>
#include <wctype.h>  // towupper()

#include "mycpp/common.h"
#include "vendor/greatest.h"

TEST casefold_demo() {
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

TEST upper_lower_demo() {
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

  RUN_TEST(upper_lower_demo);
  RUN_TEST(isspace_demo);

  // Crashes in CI?  Because of Turkish locale?
  // RUN_TEST(casefold_test);

  // gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
