// libc.h: Replacement for native/libc.c

#ifndef LIBC_H
#define LIBC_H

#include <fnmatch.h>
#include <unistd.h>  // gethostname()

#include "mylib.h"

namespace libc {

inline Str* gethostname() {
  char* buf = static_cast<char*>(malloc(HOST_NAME_MAX + 1));
  int result = ::gethostname(buf, PATH_MAX);
  if (result != 0) {
    // TODO: print errno, e.g. ENAMETOOLONG (glibc)
    throw new RuntimeError(new Str("Couldn't get working directory"));
  }
  return new Str(buf);
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

inline Str* realpath(Str* path) {
  assert(0);
}

}  // namespace libc

#endif  // LIBC_H
