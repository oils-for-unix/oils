// stdlib.h: Replacement for native/posixmodule.c

#ifndef LEAKY_STDLIB_H
#define LEAKY_STDLIB_H

#include <errno.h>
#include <sys/types.h>  // mode_t
#include <unistd.h>

#include "mycpp/runtime.h"

namespace fcntl_ {

// for F_GETFD
int fcntl(int fd, int cmd);
int fcntl(int fd, int cmd, int arg);

}  // namespace fcntl_

namespace posix {

mode_t umask(mode_t mask);

inline int access(Str* pathname, int mode) {
  return ::access(pathname->data_, mode) == 0;
}

inline Str* getcwd() {
  Str* result = OverAllocatedStr(PATH_MAX);
  char* p = ::getcwd(result->data_, PATH_MAX);
  if (p == nullptr) {
    throw Alloc<OSError>(errno);
  }
  // Important: set the length of the string!
  result->SetObjLenFromC();
  return result;
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
  return StrFromC(::strerror(err_num));
}

inline Tuple2<int, int> pipe() {
  int fd[2];
  if (::pipe(fd) < 0) {
    // TODO: handle errno
    assert(0);
  }
  return Tuple2<int, int>(fd[0], fd[1]);
}

inline int close(int fd) {
  // TODO: handle errno.  Although I'm not sure if it happens!
  return ::close(fd);
}

void putenv(Str* name, Str* value);

inline int fork() {
  return ::fork();
}

inline void _exit(int status) {
  ::_exit(status);
}

inline void write(int fd, Str* s) {
  ::write(fd, s->data_, len(s));
}

// Can we use fcntl instead?
void dup2(int oldfd, int newfd);

int open(Str* path, int flags, int perms);

mylib::LineReader* fdopen(int fd, Str* c_mode);

void execve(Str* argv0, List<Str*>* argv, Dict<Str*, Str*>* environ);

void kill(int pid, int sig);

}  // namespace posix

namespace time_ {

void tzset();
time_t time();
time_t localtime(time_t ts);
Str* strftime(Str* s, time_t ts);

}  // namespace time_

#endif  // LEAKY_STDLIB_H
