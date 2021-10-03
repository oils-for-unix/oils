#define _GNU_SOURCE 1
#include <fnmatch.h>
#include <stdio.h>

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
  char* pattern = "@(spam|foo\\|)";
  char* str = "spam";

  test(pattern, "spam");
  test(pattern, "foo|");  // this should match, but it doesn't
  test(pattern, "foo\\|");  // doesn't match either

  return 0;
}
