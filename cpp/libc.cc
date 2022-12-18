// libc.cc: Replacement for pyext/libc.c

#include "cpp/libc.h"

#include <errno.h>
#include <fnmatch.h>
#include <glob.h>
#include <locale.h>
#include <regex.h>
#include <sys/ioctl.h>
#include <unistd.h>  // gethostname()
#include <wchar.h>

namespace libc {

Str* gethostname() {
  Str* result = OverAllocatedStr(HOST_NAME_MAX);
  int status = ::gethostname(result->data_, HOST_NAME_MAX);
  if (status != 0) {
    throw Alloc<OSError>(errno);
  }
  // Important: set the length of the string!
  result->SetObjLenFromC();
  return result;
}

int fnmatch(Str* pat, Str* str) {
  int flags = FNM_EXTMATCH;
  int result = ::fnmatch(pat->data_, str->data_, flags);
  switch (result) {
  case 0:
    return 1;
  case FNM_NOMATCH:
    return 0;
  default:
    // Other error
    return -1;
  }
}

List<Str*>* glob(Str* pat) {
  glob_t results;
  // Hm, it's weird that the first one can't be called with GLOB_APPEND.  You
  // get a segfault.
  int flags = 0;
  // int flags = GLOB_APPEND;
  // flags |= GLOB_NOMAGIC;
  int ret = glob(pat->data_, flags, NULL, &results);

  const char* err_str = NULL;
  switch (ret) {
  case 0:  // no error
    break;
  case GLOB_ABORTED:
    err_str = "read error";
    break;
  case GLOB_NOMATCH:
    // No error, because not matching isn't necessarily a problem.
    // NOTE: This can be turned on to log overaggressive calls to glob().
    // err_str = "nothing matched";
    break;
  case GLOB_NOSPACE:
    err_str = "no dynamic memory";
    break;
  default:
    err_str = "unknown problem";
    break;
  }
  if (err_str) {
    throw Alloc<RuntimeError>(StrFromC(err_str));
  }

  // http://stackoverflow.com/questions/3512414/does-this-pylist-appendlist-py-buildvalue-leak
  size_t n = results.gl_pathc;
  auto matches = NewList<Str*>();

  // Print array of results
  size_t i;
  for (i = 0; i < n; i++) {
    const char* m = results.gl_pathv[i];
    matches->append(StrFromC(m));
  }
  globfree(&results);

  return matches;
}

// Raises RuntimeError if the pattern is invalid.  TODO: Use a different
// exception?
List<Str*>* regex_match(Str* pattern, Str* str) {
  List<Str*>* results = NewList<Str*>();

  regex_t pat;
  if (regcomp(&pat, pattern->data_, REG_EXTENDED) != 0) {
    // TODO: check error code, as in func_regex_parse()
    throw Alloc<RuntimeError>(StrFromC("Invalid regex syntax (regex_match)"));
  }

  int outlen = pat.re_nsub + 1;  // number of captures

  const char* s0 = str->data_;
  regmatch_t* pmatch =
      static_cast<regmatch_t*>(malloc(sizeof(regmatch_t) * outlen));
  int match = regexec(&pat, s0, outlen, pmatch, 0) == 0;
  if (match) {
    int i;
    for (i = 0; i < outlen; i++) {
      int len = pmatch[i].rm_eo - pmatch[i].rm_so;
      Str* m = StrFromC(s0 + pmatch[i].rm_so, len);
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

// Odd: This a Tuple2* not Tuple2 because it's Optional[Tuple2]!
Tuple2<int, int>* regex_first_group_match(Str* pattern, Str* str, int pos) {
  regex_t pat;
  regmatch_t m[NMATCH];

  const char* old_locale = setlocale(LC_CTYPE, NULL);

  if (setlocale(LC_CTYPE, "") == NULL) {
    throw Alloc<RuntimeError>(StrFromC("Invalid locale for LC_CTYPE"));
  }

  // Could have been checked by regex_parse for [[ =~ ]], but not for glob
  // patterns like ${foo/x*/y}.

  if (regcomp(&pat, pattern->data_, REG_EXTENDED) != 0) {
    throw Alloc<RuntimeError>(
        StrFromC("Invalid regex syntax (func_regex_first_group_match)"));
  }

  // Match at offset 'pos'
  int result = regexec(&pat, str->data_ + pos, NMATCH, m, 0 /*flags*/);
  regfree(&pat);

  setlocale(LC_CTYPE, old_locale);

  if (result != 0) {
    return nullptr;
  }

  // Assume there is a match
  regoff_t start = m[1].rm_so;
  regoff_t end = m[1].rm_eo;
  Tuple2<int, int>* tup = Alloc<Tuple2<int, int>>(pos + start, pos + end);

  return tup;
}

int wcswidth(Str* str) {
  int len = mbstowcs(NULL, str->data(), 0);
  if (len == -1) {
    throw Alloc<UnicodeError>(StrFromC("mbstowcs error: Invalid UTF-8 string"));
  }

  auto* unicode = static_cast<wchar_t*>(malloc(len + 1));
  assert(unicode != nullptr);
  mbstowcs(unicode, str->data(), len + 1);
  int width = ::wcswidth(unicode, len + 1);
  free(unicode);

  return width;
}

int get_terminal_width() {
  struct winsize w;
  if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &w) == -1) {
    throw Alloc<IOError>(errno);
  }
  return w.ws_col;
}

}  // namespace libc
