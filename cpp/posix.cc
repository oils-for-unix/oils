// posix.cc: Replacement for native/posixmodule.c

#include "posix.h"

#include <fcntl.h>     // open
#include <sys/wait.h>  // WUNTRACED
#include <unistd.h>

namespace posix {

int open(Str* path, int flags, int perms) {
  mylib::Str0 path0(path);
  return ::open(path0.Get(), flags, perms);
}

}  // namespace posix
