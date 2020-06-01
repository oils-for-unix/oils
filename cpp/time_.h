// time.h

#ifndef TIME_H
#define TIME_H

#include "mylib.h"

namespace time_ {

void* tzset() {
  assert(0);
}

int time() {
  assert(0);
}

// TODO: Should these be bigger integers?
int localtime(int ts) {
  assert(0);
}

Str* strftime(Str* s, int ts) {
  assert(0);
}
 
}  // namespace time

#endif  // TIME_H

