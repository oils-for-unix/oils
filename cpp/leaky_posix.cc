// posix.cc: Replacement for native/posixmodule.c

// clang-format off
#include "mycpp/myerror.h"  // for OSError; must come first
// clang-format on

#include "leaky_posix.h"

#include <errno.h>
#include <fcntl.h>      // open
#include <sys/stat.h>   // umask
#include <sys/types.h>  // umask
#include <sys/wait.h>   // WUNTRACED
#include <unistd.h>

namespace posix {

int umask(int mask) {
  // note: assuming mode_t fits in an int
  return ::umask(mask);
}

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
