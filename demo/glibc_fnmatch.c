#define _GNU_SOURCE 1
#include <fnmatch.h>
#include <stdio.h>

/*
 * BUG: When FNM_EXTMATCH is passed, you should be able to escape | as \| 
 * just like you can escape * as \*.
 *
 * (Remember that \| is written "\\|" in C syntax)
 */


void test(char* pattern, char* str) {
  int ret = fnmatch(pattern, str, FNM_EXTMATCH);

  switch (ret) {
  case 0:
    printf("%-10s   matches         %-10s\n", str, pattern);
    break;
  case FNM_NOMATCH:
    printf("%-10s   doesn't match   %-10s\n", str, pattern);
    break;
  default:
    printf("other error: %s\n", str);
    break;
  }
}

int main() {
  char* pattern = "@(spam|foo\\||bar\\*)";
  char* str = "spam";

  test(pattern, "spam");

  test(pattern, "bar*");  // escaping works
  test(pattern, "bar\\");  // shouldn't match

  test(pattern, "foo|");  // BUG: this should match, but it doesn't
  test(pattern, "foo\\|");  // shouldn't match and doesn't match

  return 0;
}
