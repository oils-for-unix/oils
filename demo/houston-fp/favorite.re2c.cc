// re2c example
//
// Similar to https://re2c.org/manual/manual_c.html

// Demos:
//
// - Unhandled input
// - Unreachable code

#include <stdio.h>  // printf

bool MatchDoubleQuotedString(const char *s) {
  const char *YYCURSOR = s;
  const char *YYMARKER;   // sometimes needed

  //for (;;) {
  /*!re2c
    re2c:yyfill:enable = 0;
    re2c:define:YYCTYPE = char;

    favorite = ["] ( [^\x00"\\] | "\\." )* ["];

    favorite  { return true; }
    *         { return false; }
  */
  //}
}

int main(int argc, char **argv) {
  char *s = argv[1];
  bool matched = MatchDoubleQuotedString(s);

  if (matched) {
    printf("YES   %s\n", s);
  } else {
    printf("NO    %s\n", s);
  }

  return 0;
}
