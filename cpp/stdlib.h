// cpp/stdlib.h: Replacement for pyext/posixmodule.c

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

inline bool access(BigStr* pathname, int mode) {
  // No error case: 0 is success, -1 is error AND false.
  return ::access(pathname->data_, mode) == 0;
}

inline BigStr* getcwd() {
  BigStr* result = OverAllocatedStr(PATH_MAX);
  char* p = ::getcwd(result->data_, PATH_MAX);
  if (p == nullptr) {
    throw Alloc<OSError>(errno);
  }
  // Important: set the length of the string!
  result->MaybeShrink(strlen(result->data_));
  return result;
}

// No error cases: the man page says these get*() functions always succeed

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
  // No error case: false is the same as error (e.g. in pyext/posixmodule.c)
  return ::isatty(fd);
}

inline BigStr* strerror(int err_num) {
  // No error case: returns an appropriate string if err_num is invalid
  return StrFromC(::strerror(err_num));
}

inline Tuple2<int, int> pipe() {
  int fd[2];
  if (::pipe(fd) < 0) {
    throw Alloc<OSError>(errno);
  }
  return Tuple2<int, int>(fd[0], fd[1]);
}

inline void close(int fd) {
  if (::close(fd) < 0) {
    throw Alloc<OSError>(errno);
  }
}

void putenv(BigStr* name, BigStr* value);

inline int fork() {
  int result = ::fork();
  if (result < 0) {
    throw Alloc<OSError>(errno);
  }
  return result;
}

inline void _exit(int status) {
  // No error case: does not return
  ::_exit(status);
}

inline void write(int fd, BigStr* s) {
  //
  // IMPORTANT TODO: Write in a loop like posix_write() in pyext/posixmodule.c
  //

  if (::write(fd, s->data_, len(s)) < 0) {
    throw Alloc<OSError>(errno);
  }
}

inline void setpgid(pid_t pid, pid_t pgid) {
  int ret = ::setpgid(pid, pgid);
  if (ret < 0) {
    throw Alloc<OSError>(errno);
  }
}

inline int getpgid(pid_t pid) {
  pid_t ret = ::getpgid(pid);
  if (ret < 0) {
    throw Alloc<OSError>(errno);
  }
  return ret;
}

inline void tcsetpgrp(int fd, pid_t pgid) {
  int ret = ::tcsetpgrp(fd, pgid);
  if (ret < 0) {
    throw Alloc<OSError>(errno);
  }
}

inline int tcgetpgrp(int fd) {
  pid_t ret = ::tcgetpgrp(fd);
  if (ret < 0) {
    throw Alloc<OSError>(errno);
  }
  return ret;
}

// Can we use fcntl instead?
void dup2(int oldfd, int newfd);

int open(BigStr* path, int flags, int perms);

mylib::File* fdopen(int fd, BigStr* c_mode);

void execve(BigStr* argv0, List<BigStr*>* argv,
            Dict<BigStr*, BigStr*>* environ);

void kill(int pid, int sig);
void killpg(int pgid, int sig);

List<BigStr*>* listdir(BigStr* path);

}  // namespace posix

namespace time_ {

void tzset();
time_t time();
// Note: This is translated in a weird way, unlike Python's API.  Might want to
// factor out our own API with better types.
time_t localtime(time_t ts);
BigStr* strftime(BigStr* s, time_t ts);
void sleep(int seconds);

}  // namespace time_

#endif  // LEAKY_STDLIB_H
