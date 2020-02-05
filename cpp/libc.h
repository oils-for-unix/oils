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
void glob() {
  assert(0);
}

void regex_match() {
  assert(0);
}

void regex_first_group_match() {
  assert(0);
}

}  // namespace libc

#endif  // LIBC_H
