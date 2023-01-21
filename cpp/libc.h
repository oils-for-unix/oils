// libc.h: Replacement for native/libc.c

#ifndef LIBC_H
#define LIBC_H

#include <stdlib.h>

#include "mycpp/runtime.h"

namespace libc {

// TODO: SHARE with pyext
inline void print_time(double real, double user, double sys) {
  fprintf(stderr, "real\t%.3f\n", real);
  fprintf(stderr, "user\t%.3f\n", user);
  fprintf(stderr, "sys\t%.3f\n", sys);
}

Str* realpath(Str* path);

Str* gethostname();

int fnmatch(Str* pat, Str* str);

List<Str*>* glob(Str* pat);

Tuple2<int, int>* regex_first_group_match(Str* pattern, Str* str, int pos);

List<Str*>* regex_match(Str* pattern, Str* str);

int wcswidth(Str* str);
int get_terminal_width();

}  // namespace libc

#endif  // LIBC_H
