// posix.cc: Replacement for native/posixmodule.c

#include "posix.h"

#include <fcntl.h>     // open
#include <sys/wait.h>  // WUNTRACED
#include <unistd.h>

// Why do I need these again here?  They are undefined in the header.
#undef X_OK
#undef R_OK
#undef W_OK
#undef O_APPEND
#undef O_CREAT
#undef O_RDONLY
#undef O_RDWR
#undef O_WRONLY
#undef O_TRUNC

namespace posix {

// Aliases in this namespace.  Avoid name conflicts with macros.
int X_OK = X_OK;
int R_OK = R_OK;
int W_OK = W_OK;
int O_APPEND = O_APPEND_;
int O_CREAT = O_CREAT_;
int O_RDONLY = O_RDONLY_;
int O_RDWR = O_RDWR_;
int O_WRONLY = O_WRONLY_;
int O_TRUNC = O_TRUNC_;

int open(Str* path, int mode, int perms) {
  mylib::Str0 path0(path);
  return ::open(path0.Get(), mode, perms);
}

}  // namespace posix
