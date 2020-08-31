// fcntl.h

#ifndef FCNTL_H
#define FCNTL_H

#include <assert.h>

#undef F_DUPFD
#undef F_GETFD

namespace fcntl_ {

extern const int F_DUPFD;
extern const int F_GETFD;

inline int fcntl(int fd, int cmd, int arg) {
  assert(0);
}

// for F_GETFD
inline int fcntl(int fd, int cmd) {
  assert(0);
}
 
}  // namespace fcntl

#endif  // FCNTL_H

