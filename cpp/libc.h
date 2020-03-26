// libc.h: Replacement for native/libc.c

#ifndef LIBC_H
#define LIBC_H

#include "mylib.h"

namespace libc {

inline Str* gethostname() {
  assert(0);
}

inline bool fnmatch(Str* s, Str* t) {
  assert(0);
}

// TODO: Write correct signatures
inline List<Str*>* glob(Str* pat) {
  assert(0);
}

// Raises RuntimeError if the pattern is invalid.  TODO: Use a different
// exception?
inline List<Str*>* regex_match(Str* pattern, Str* str) {
  assert(0);
}

inline Tuple2<int, int>* regex_first_group_match(Str* pattern, Str* str, int pos) {
  assert(0);
}

inline void print_time(double real, double user, double sys) {
  assert(0);
}

}  // namespace libc

#endif  // LIBC_H
