// fcntl.h

#ifndef FCNTL_H
#define FCNTL_H

#include <fcntl.h>

namespace fcntl_ {

// for F_GETFD
int fcntl(int fd, int cmd);
int fcntl(int fd, int cmd, int arg);

}  // namespace fcntl_

#endif  // FCNTL_H
