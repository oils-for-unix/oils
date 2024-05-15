// re2c example
//
// Similar to https://re2c.org/manual/manual_c.html

// Demos:
//
// - Unreachable code - add unreachable
// - Unhandled input - comment out * clause (more convincing in our huge lexer)

#include <assert.h>  // assert
#include <stdio.h>  // printf


/*!re2c
  re2c:yyfill:enable = 0;
  re2c:define:YYCTYPE = char;

  // Define rule for C-style strings with backslash escapes.
  //
  // \x00 is for the sentinel.  re2c warns you that the sentinel should not be
  // matched in a pattern.

  favorite = ["] ( [^\x00"\\] | "\\" [^\x00] )* ["];

  unreachable = "\"\"";

  favorite2 = ["] ( [^\x00"\\] | "\\z" )* ["];
*/

bool MatchDoubleQuotedString(const char *s) {
  const char *YYCURSOR = s;
  const char *YYMARKER;   // depending on pattern, generated code may use this

  /*!re2c
    favorite  { return true; }
    *         { return false; }
  */

  assert(0);
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
