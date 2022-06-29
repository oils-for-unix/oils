// time.h

#ifndef TIME_H
#define TIME_H

#include <time.h>

#include "mycpp/mylib.h"

namespace time_ {

inline void* tzset() {
  NotImplemented();
}

inline int time() {
  return ::time(nullptr);
}

// TODO: Should these be bigger integers?
inline int localtime(int ts) {
  NotImplemented();
}

inline Str* strftime(Str* s, int ts) {
  NotImplemented();
}

}  // namespace time_

#endif  // TIME_H
