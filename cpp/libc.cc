// libc.cc: Replacement for native/libcmodule.c

#include "libc.h"
#include <regex.h>

namespace libc {

// Raises RuntimeError if the pattern is invalid.  TODO: Use a different
// exception?
List<Str*>* regex_match(Str* pattern, Str* str) {
  List<Str*>* results = new List<Str*>();

  const char* c_pattern = copy0(pattern);
  const char* c_str = copy0(str);

  regex_t pat;
  if (regcomp(&pat, c_pattern, REG_EXTENDED) != 0) {
    // TODO: check error code, as in func_regex_parse()
    throw new RuntimeError(new Str("Invalid regex syntax (regex_match)"));
  }

  int outlen = pat.re_nsub + 1;

  int match;
  regmatch_t *pmatch = (regmatch_t*) malloc(sizeof(regmatch_t) * outlen);
  if (match = (regexec(&pat, c_str, outlen, pmatch, 0) == 0)) {
    int i;
    for (i = 0; i < outlen; i++) {
      int len = pmatch[i].rm_eo - pmatch[i].rm_so;
      Str* m = new Str(c_str + pmatch[i].rm_so, len);
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


}  // namespace libc
