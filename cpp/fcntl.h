// fcntl.h

#ifndef FCNTL_H
#define FCNTL_H

#include <assert.h>

namespace fcntl {

extern int F_DUPFD;
extern int F_GETFD;

inline int fcntl(int fd, int cmd, int arg) {
  assert(0);
}
 
}  // namespace fcntl

#endif  // FCNTL_H

