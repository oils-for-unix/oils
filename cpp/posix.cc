// posix.cc: Replacement for native/posixmodule.c

// clang-format off
#include "myerror.h"  // for OSError; must come first
// clang-format on

#include "posix.h"

#include <fcntl.h>     // open
#include <sys/wait.h>  // WUNTRACED
#include <unistd.h>

namespace posix {

int open(Str* path, int flags, int perms) {
  mylib::Str0 path0(path);
  return ::open(path0.Get(), flags, perms);
}

void dup2(int oldfd, int newfd) {
  if (::dup2(oldfd, newfd) < 0) {
    throw new OSError(errno);
  }
}

}  // namespace posix
