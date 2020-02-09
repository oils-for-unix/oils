// posix.h: Replacement for native/posixmodule.c

#ifndef POSIX_H
#define POSIX_H

#include "mylib.h"

namespace posix {

// aliases in this namespace
extern int X_OK;
extern int R_OK;
extern int W_OK;

int access(Str* pathname, int mode) {
  assert(0);
}

Str* getcwd() {
  assert(0);
}

int getegid() {
  assert(0);
}

int geteuid() {
  assert(0);
}

int getpid() {
  assert(0);
}

int getppid() {
  assert(0);
}

int getuid() {
  assert(0);
}

bool isatty(int fd) {
  assert(0);
}

Str* strerror(int errno) {
  assert(0);
}

Str* uname() {
  assert(0);
}

// TODO: write proper signatures
// stat returns stat_result
void stat() {
  assert(0);
}

void lstat() {
  assert(0);
}

// replace with getenv() and setenv()?
int environ;

// Dummy exception posix::error
class error {};

}  // namespace posix

#endif  // POSIX_H
