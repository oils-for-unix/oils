// fcntl.h

#ifndef FCNTL_H
#define FCNTL_H

#include <assert.h>
#include <fcntl.h>

#undef F_DUPFD
#undef F_GETFD

namespace fcntl_ {

extern const int F_DUPFD;
extern const int F_GETFD;

inline int fcntl(int fd, int cmd, int arg) {
  // TODO: handle errno
  return ::fcntl(fd, cmd, arg);
}

// for F_GETFD
inline int fcntl(int fd, int cmd) {
  // TODO: handle errno
  return ::fcntl(fd, cmd);
}

}  // namespace fcntl_

#endif  // FCNTL_H
