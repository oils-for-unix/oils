// libc.h: Replacement for native/libc.c

#ifndef LIBC_H
#define LIBC_H

#include <langinfo.h>  // using CODESET
#include <locale.h>    // using LC_CTYPE
#include <stdlib.h>

#include "mycpp/runtime.h"

namespace libc {

// TODO: SHARE with pyext
inline void print_time(double real, double user, double sys) {
  fprintf(stderr, "real\t%.3f\n", real);
  fprintf(stderr, "user\t%.3f\n", user);
  fprintf(stderr, "sys\t%.3f\n", sys);
}

BigStr* realpath(BigStr* path);

BigStr* gethostname();

int fnmatch(BigStr* pat, BigStr* str, int flags = 0);

List<BigStr*>* glob(BigStr* pat, int flags = 0);

Tuple2<int, int>* regex_first_group_match(BigStr* pattern, BigStr* str,
                                          int pos);

List<int>* regex_search(BigStr* pattern, int cflags, BigStr* str, int eflags,
                        int pos = 0);

int wcswidth(BigStr* str);
int get_terminal_width();
int sleep_until_error(double seconds);

}  // namespace libc

// pylib/locale_.py
namespace pylocale {
  const int CODESET = ::CODESET;
constexpr int lc_ctype = LC_CTYPE;
#undef LC_CTYPE
  const int LC_CTYPE = lc_ctype;

class Error {
 public:
  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(kZeroMask, sizeof(Error));
  }
};
BigStr* setlocale(int category, BigStr* locale);
BigStr* nl_langinfo(int item);
}  // namespace locale

#endif  // LIBC_H
