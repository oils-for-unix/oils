// time.h

#ifndef TIME_H
#define TIME_H

#include <time.h>
#include "mylib.h"

namespace time_ {

void* tzset() {
  assert(0);
}

int time() {
  return ::time(nullptr);
}

// TODO: Should these be bigger integers?
int localtime(int ts) {
  assert(0);
}

Str* strftime(Str* s, int ts) {
  assert(0);
}

}  // namespace time_

#endif  // TIME_H
