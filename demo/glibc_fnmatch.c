#define _GNU_SOURCE 1
#include <fnmatch.h>
#include <stdio.h>

/*
 * BUG: When FNM_EXTMATCH is passed, you should be able to escape | as \|
 * just like you can escape * as \*.
 *
 * (Remember that \| is written "\\|" in C syntax)
 */

void test(char* pattern, char* str, int flags) {
  int ret = fnmatch(pattern, str, flags);

  char* prefix = (flags == FNM_EXTMATCH) ? "[ext]" : "     ";

  switch (ret) {
  case 0:
    printf("%s   %-10s   matches         %-10s\n", prefix, str, pattern);
    break;
  case FNM_NOMATCH:
    printf("%s   %-10s   doesn't match   %-10s\n", prefix, str, pattern);
    break;
  default:
    printf("other error: %s\n", str);
    break;
  }
}

int main() {
  char* pattern = 0;

  // Demonstrate that \| and \* are valid patterns, whether or not FNM_EXTMATCH
  // is set
  pattern = "\\*";
  test(pattern, "*", FNM_EXTMATCH);
  test(pattern, "x", FNM_EXTMATCH);
  printf("\n");

  pattern = "\\|";
  test(pattern, "|", 0);
  test(pattern, "x", 0);
  test(pattern, "|", FNM_EXTMATCH);
  test(pattern, "x", FNM_EXTMATCH);
  printf("\n");

  // Wrap in @() works for \*
  pattern = "@(\\*)";
  test(pattern, "*", FNM_EXTMATCH);
  test(pattern, "x", FNM_EXTMATCH);
  printf("\n");

  // Wrap in @() doesn't work for \|
  pattern = "@(\\|)";
  test(pattern, "|", FNM_EXTMATCH);  // BUG: doesn't match
  test(pattern, "x", FNM_EXTMATCH);
  printf("\n");

  // More realistic example
  pattern = "@(spam|foo\\||bar\\*)";

  // Demonstrate that \* escaping works
  test(pattern, "bar*", FNM_EXTMATCH);
  test(pattern, "bar\\", FNM_EXTMATCH);

  test(pattern, "foo|",
       FNM_EXTMATCH);  // BUG: this should match, but it doesn't
  test(pattern, "foo\\|", FNM_EXTMATCH);  // shouldn't match and doesn't match

  return 0;
}
