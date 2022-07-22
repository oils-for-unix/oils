// leaky_libc.h: Replacement for native/libc.c

#ifndef LIBC_H
#define LIBC_H

#include <fnmatch.h>
#include <limits.h>
#include <stdlib.h>
#include <unistd.h>  // gethostname()

#include "mycpp/mylib_old.h"

namespace libc {

inline Str* realpath(Str* path) {
  assert(path->IsNulTerminated());
  char* rp = ::realpath(path->data_, 0);
  return new Str(rp);
}

inline Str* gethostname() {
  char* buf = static_cast<char*>(malloc(HOST_NAME_MAX + 1));
  int result = ::gethostname(buf, PATH_MAX);
  if (result != 0) {
    // TODO: print errno, e.g. ENAMETOOLONG (glibc)
    throw new RuntimeError(new Str("Couldn't get working directory"));
  }
  return new Str(buf);
}

inline bool fnmatch(Str* pat, Str* str) {
  // copy into NUL-terminated buffers
  mylib::Str0 pat0(pat);
  mylib::Str0 str0(str);
  int flags = FNM_EXTMATCH;
  bool result = ::fnmatch(pat0.Get(), str0.Get(), flags) == 0;
  return result;
}

List<Str*>* glob(Str* pat);

List<Str*>* regex_match(Str* pattern, Str* str);

Tuple2<int, int>* regex_first_group_match(Str* pattern, Str* str, int pos);

inline void print_time(double real_time, double user_time, double system_time) {
  // TODO(Jesse): How to we report CPU load? .. Do we need to?
  printf("%1.2fs user %1.2fs system BUG cpu %1.3f total", user_time,
         system_time, real_time);  // 0.05s user 0.03s system 2% cpu 3.186 total
}

}  // namespace libc

#endif  // LIBC_H
