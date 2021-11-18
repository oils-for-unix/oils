// posix.cc: Replacement for native/posixmodule.c

#include "posix.h"

#include <fcntl.h>     // open
#include <sys/wait.h>  // WUNTRACED
#include <unistd.h>

namespace posix {

int open(Str* path, int flags, int perms) {
  mylib::Str0 path0(path);
  log("OPEN %s\n", path0.Get());
  log("flags %d\n", flags);
  log("O_CREAT %d\n", O_CREAT);
  log("O_RDWR %d\n", O_RDWR);

  log("perms %d\n", perms);
  int fd = ::open(path0.Get(), flags, perms);
  log("fd = %d\n", fd);
  return fd;
}

}  // namespace posix
