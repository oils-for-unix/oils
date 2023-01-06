#ifndef FANOS_H
#define FANOS_H

#include "mycpp/runtime.h"

namespace fanos {

void send(int sock_fd, Str* blob);

Str* recv(int sock_fd, List<int>* fd_out);

}  // namespace fanos

#endif  // FANOS_H
