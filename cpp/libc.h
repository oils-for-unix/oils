// libc.h: Replacement for native/libc.c

#ifndef LIBC_H
#define LIBC_H

#include <fnmatch.h>

#include "mylib.h"

namespace libc {

inline Str* gethostname() {
  assert(0);
}

inline bool fnmatch(Str* pat, Str* str, bool extglob) {
  // copy into NUL-terminated buffers
  mylib::Str0 pat0(pat);
  mylib::Str0 str0(str);
  int flags = extglob ? FNM_EXTMATCH : 0;
  bool result = ::fnmatch(pat0.Get(), str0.Get(), flags) == 0;
  return result;
}

List<Str*>* glob(Str* pat);

List<Str*>* regex_match(Str* pattern, Str* str);

Tuple2<int, int>* regex_first_group_match(Str* pattern, Str* str, int pos);

inline void print_time(double real, double user, double sys) {
  assert(0);
}

}  // namespace libc

#endif  // LIBC_H
