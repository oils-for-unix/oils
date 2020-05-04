// libc.h: Replacement for native/libc.c

#ifndef LIBC_H
#define LIBC_H

#include <fnmatch.h>

#include "mylib.h"

namespace libc {

inline Str* gethostname() {
  assert(0);
}

// Copy a Str* to a NUL-terminated C string.  TODO: Could we have two different
// types and avoid these copies?
inline char* copy0(Str* s) {
  char* s0 = static_cast<char*>(malloc(s->len_ + 1));
  memcpy(s0, s->data_, s->len_);
  s0[s->len_] = '\0';
  return s0;
}

inline bool fnmatch(Str* pat, Str* str) {
  // copy into NUL-terminated buffers
  char* pat0 = copy0(pat);
  char* str0 = copy0(str);
  bool result = ::fnmatch(pat0, str0, 0) == 0;
  free(pat0);
  free(str0);
  return result;
}

inline List<Str*>* glob(Str* pat) {
  assert(0);
}

// Raises RuntimeError if the pattern is invalid.  TODO: Use a different
// exception?
inline List<Str*>* regex_match(Str* pattern, Str* str) {
  assert(0);
}

inline Tuple2<int, int>* regex_first_group_match(Str* pattern, Str* str,
                                                 int pos) {
  assert(0);
}

inline void print_time(double real, double user, double sys) {
  assert(0);
}

}  // namespace libc

#endif  // LIBC_H
