// posix.h: Replacement for native/posixmodule.c

#ifndef POSIX_H
#define POSIX_H

#include <unistd.h>

#include "mylib.h"

namespace posix {

// aliases in this namespace
extern int X_OK_;
extern int R_OK_;
extern int W_OK_;

inline int access(Str* pathname, int mode) {
  assert(0);
}

inline Str* getcwd() {
  assert(0);
}

inline int getegid() {
  assert(0);
}

inline int geteuid() {
  assert(0);
}

inline int getpid() {
  return ::getpid();
}

inline int getppid() {
  assert(0);
}

inline int getuid() {
  assert(0);
}

inline bool isatty(int fd) {
  assert(0);
}

inline Str* strerror(int errno) {
  assert(0);
}

inline Str* uname() {
  assert(0);
}

// TODO: write proper signatures
// stat returns stat_result
inline void stat() {
  assert(0);
}

inline void lstat() {
  assert(0);
}

inline Tuple2<int, int> pipe() {
  assert(0);
}

inline void close(int fd) {
  assert(0);
}

// Dummy exception posix::error
class error {};

}  // namespace posix

#endif  // POSIX_H
