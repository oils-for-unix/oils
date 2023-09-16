#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

/*!re2c

  re2c:yyfill:enable = 0;
  re2c:define:YYCTYPE = char;
  re2c:define:YYCURSOR = p;
*/

int lex(const char *s) {
  const char *p = s;  // mutated by re2c
  const char *YYMARKER = s;

  int result = 0;

  while (1) {
  /*!re2c

    number = [1-9][0-9]*;

    // any number of unescaped, followed by any number of escapes
    // dq_string = ["] ( [^"\x00\n"\\]* (\\.)* )* ["];

    not_end = [^\x00\n];

    dq_string = ["] ( [^\x00\n"\\] | "\\" not_end )* ["];
    comment = "#" not_end*;

    // TODO:
    // # comments
    // C++ char literals

    dq_string { result = 1; break; }
    comment   { result = 2; break; }
    *         { result = 3; break;; }
  */
  }

  int len = p - s;
  printf("  len=%d\n", len);
  return result;
}

int main(int argc, char **argv) {

  // TODO: 
  // - make sure the whole thing matches
  // - wrap in Python API
  // - wrap in command line API with TSV?

  if (argc == 1) {
    printf("TODO: filter stdin\n");
    // TODO:
    // - getline() one at a time from the file, or just from stdin
  } else {
    for (int i = 0; i < argc; ++i) {
      char* s = argv[i];
      printf("\n");
      int result = lex(s);
      printf("%d %d %s\n", result, strlen(s), s);
    }
  }
  return 0;
}
