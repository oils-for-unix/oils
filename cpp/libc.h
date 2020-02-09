// libc.h: Replacement for native/libc.c

#ifndef LIBC_H
#define LIBC_H

#include "mylib.h"

namespace libc {

Str* gethostname() {
  assert(0);
}

bool fnmatch(Str* s, Str* t) {
  assert(0);
}

// TODO: Write correct signatures
List<Str*>* glob(Str* pat) {
  assert(0);
}

// Raises RuntimeError if the pattern is invalid.  TODO: Use a different
// exception?
List<Str*>* regex_match(Str* pattern, Str* str) {
  assert(0);
}

Tuple2<int, int>* regex_first_group_match(Str* pattern, Str* str, int pos) {
  assert(0);
}

}  // namespace libc

#endif  // LIBC_H
