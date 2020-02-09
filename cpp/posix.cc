// posix.cc: Replacement for native/posixmodule.c

#include "posix.h"

#include <unistd.h>

namespace posix {

int X_OK = ::X_OK;
int R_OK = ::R_OK;
int W_OK = ::W_OK;

}  // namespace posix
