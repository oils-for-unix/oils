// leaky_libc.h: Replacement for native/libc.c

#ifndef LIBC_H
#define LIBC_H

#include <fnmatch.h>
#include <stdlib.h>

#include "mycpp/runtime.h"

namespace libc {

inline bool fnmatch(Str* pat, Str* str) {
  int flags = FNM_EXTMATCH;
  bool result = ::fnmatch(pat->data(), str->data(), flags) == 0;
  return result;
}

inline void print_time(double real_time, double user_time, double system_time) {
  fprintf(stderr, "%1.2fs user\n%1.2fs system\n%1.3fs total\n", user_time,
         system_time, real_time);  // 0.05s user 0.03s system 3.186s total
}

inline Str* realpath(Str* path) {
  char* rp = ::realpath(path->data_, 0);
  return StrFromC(rp);
}

Str* gethostname();

List<Str*>* glob(Str* pat);

Tuple2<int, int>* regex_first_group_match(Str* pattern, Str* str, int pos);

List<Str*>* regex_match(Str* pattern, Str* str);

}  // namespace libc

#endif  // LIBC_H
