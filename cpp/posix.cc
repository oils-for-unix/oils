// posix.cc: Replacement for native/posixmodule.c

#include "posix.h"

#include <unistd.h>

namespace posix {

// Aliases in this namespace.  Avoid name conflicts with macros.
int X_OK_ = X_OK;
int R_OK_ = R_OK;
int W_OK_ = W_OK;
int O_APPEND = O_APPEND;
int O_CREAT = O_CREAT;
int O_RDONLY = O_RDONLY;
int O_RDWR = O_RDWR;
int O_WRONLY = O_WRONLY;
int O_TRUNC = O_TRUNC;

}  // namespace posix
