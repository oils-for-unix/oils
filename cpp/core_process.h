// core_process.h

#ifndef CORE_PROCESS_H
#define CORE_PROCESS_H

#include "mylib.h"

namespace process {

class FdState {
 public:
  mylib::LineReader* Open(Str* path) {
    assert(0);
  }
};

}  // namespace process

#endif  // CORE_PROCESS_H
