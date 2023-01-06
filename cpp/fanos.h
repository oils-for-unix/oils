#ifndef FANOS_H
#define FANOS_H

// C++ interface for FANOS protocol.  A wrapper around cpp/fanos_shared.h

#include "mycpp/runtime.h"

namespace fanos {

void send(int sock_fd, Str* blob);

// Returns the decoded netstring payload and file descriptors.  The payload is
// nullptr (Python None) on EOF.
Str* recv(int sock_fd, List<int>* fd_out);

}  // namespace fanos

#endif  // FANOS_H
