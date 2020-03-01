// posix.cc: Replacement for native/posixmodule.c

#include "posix.h"

#include <unistd.h>

namespace posix {

// Aliases in this namespace.  Avoid name conflicts with macros.
int X_OK_ = X_OK;
int R_OK_ = R_OK;
int W_OK_ = W_OK;

}  // namespace posix
