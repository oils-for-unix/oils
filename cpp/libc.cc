// libc.cc: Replacement for native/libcmodule.c

#include "libc.h"
#include <regex.h>

namespace libc {

// Raises RuntimeError if the pattern is invalid.  TODO: Use a different
// exception?
List<Str*>* regex_match(Str* pattern, Str* str) {
  List<Str*>* results = new List<Str*>();

  mylib::Str0 pattern0(pattern);
  mylib::Str0 str0(str);

  regex_t pat;
  if (regcomp(&pat, pattern0.Get(), REG_EXTENDED) != 0) {
    // TODO: check error code, as in func_regex_parse()
    throw new RuntimeError(new Str("Invalid regex syntax (regex_match)"));
  }

  int outlen = pat.re_nsub + 1;  // number of captures

  int match;
  const char* s0 = str0.Get();
  regmatch_t* pmatch = (regmatch_t*)malloc(sizeof(regmatch_t) * outlen);
  if (match = (regexec(&pat, s0, outlen, pmatch, 0) == 0)) {
    int i;
    for (i = 0; i < outlen; i++) {
      int len = pmatch[i].rm_eo - pmatch[i].rm_so;
      Str* m = new Str(s0 + pmatch[i].rm_so, len);
      results->append(m);
    }
  }

  free(pmatch);
  regfree(&pat);

  if (!match) {
    return nullptr;
  }

  return results;
}

// For ${//}, the number of groups is always 1, so we want 2 match position
// results -- the whole regex (which we ignore), and then first group.
//
// For [[ =~ ]], do we need to count how many matches the user gave?

const int NMATCH = 2;

// Why is this a Tuple2* and not Tuple2?
Tuple2<int, int>* regex_first_group_match(Str* pattern, Str* str, int pos) {
  mylib::Str0 pattern0(pattern);
  mylib::Str0 str0(str);

  regex_t pat;
  regmatch_t m[NMATCH];

  const char* old_locale = setlocale(LC_CTYPE, NULL);

  if (setlocale(LC_CTYPE, "") == NULL) {
    throw new RuntimeError(new Str("Invalid locale for LC_CTYPE"));
  }

  // Could have been checked by regex_parse for [[ =~ ]], but not for glob
  // patterns like ${foo/x*/y}.

  if (regcomp(&pat, pattern0.Get(), REG_EXTENDED) != 0) {
    throw new RuntimeError(
        new Str("Invalid regex syntax (func_regex_first_group_match)"));
  }

  // Match at offset 'pos'
  int result = regexec(&pat, str0.Get() + pos, NMATCH, m, 0 /*flags*/);
  regfree(&pat);

  setlocale(LC_CTYPE, old_locale);

  if (result != 0) {
    return nullptr;
  }

  // Assume there is a match
  regoff_t start = m[1].rm_so;
  regoff_t end = m[1].rm_eo;
  return new Tuple2<int, int>(pos + start, pos + end);
}

}  // namespace libc
