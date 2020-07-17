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
  char* buf = static_cast<char*>(malloc(PATH_MAX + 1));

  char* result = ::getcwd(buf, PATH_MAX + 1);
  if (result == nullptr) {
    // TODO: print errno, e.g. ENAMETOOLONG
    throw new RuntimeError(new Str("Couldn't get working directory"));
  }

  return new Str(buf);
}

inline int getegid() {
  return ::getegid();
}

inline int geteuid() {
  return ::geteuid();
}

inline int getpid() {
  return ::getpid();
}

inline int getppid() {
  return ::getppid();
}

inline int getuid() {
  return ::getuid();
}

inline bool isatty(int fd) {
  return ::isatty(fd);
}

inline Str* strerror(int err_num) {
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

inline int close(int fd) {
  assert(0);
}

inline int putenv(Str* name, Str* value) {
  assert(0);
}

// TODO: errors
inline int chdir(Str* path) {
  assert(0);
}

inline Str* read(int fd, int num_requested) {
  char* buf = static_cast<char*>(malloc(num_requested + 1));
  int num_read = ::read(fd, buf, num_requested);
  buf[num_read] = '\0';
  if (num_read < 0) {
    throw new AssertionError();  // TODO: throw with errno
  }
  return new Str(buf, num_read);  // could be a short read
}

// Dummy exception posix::error
class error {};

}  // namespace posix

#endif  // POSIX_H
