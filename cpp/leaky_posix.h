// leaky_posix.h: Replacement for native/posixmodule.c

#ifndef POSIX_H
#define POSIX_H

// clang-format off
#include "mycpp/myerror.h"  // for OSError; must come first
// clang-format on

#include <errno.h>
#include <stdlib.h>  // putenv
#include <unistd.h>

#include "mycpp/mylib_leaky.h"

namespace posix {

inline int access(Str* pathname, int mode) {
  // Are there any errno I care about?
  mylib::Str0 pathname0(pathname);
  return ::access(pathname0.Get(), mode) == 0;
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
  return new Str(::strerror(err_num));
}

// TODO: write proper signatures
// stat returns stat_result
inline void stat() {
  NotImplemented();  // Uncalled
}

inline void lstat() {
  NotImplemented();  // Uncalled
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

inline void putenv(Str* name, Str* value) {
  assert(name->IsNulTerminated());
  assert(value->IsNulTerminated());
  int overwrite = 1;
  int ret = ::setenv(name->data_, value->data_, overwrite);
  if (ret < 0) {
    throw new IOError(errno);
  }
}

inline int fork() {
  return ::fork();
}

inline void _exit(int status) {
  exit(status);
}

inline void write(int fd, Str* s) {
  ::write(fd, s->data_, s->len_);
}

// Can we use fcntl instead?
void dup2(int oldfd, int newfd);

int open(Str* path, int flags, int perms);

inline mylib::LineReader* fdopen(int fd, Str* c_mode) {
  mylib::Str0 c_mode0(c_mode);
  FILE* f = ::fdopen(fd, c_mode0.Get());

  // TODO: raise exception
  assert(f);

  return new mylib::CFileLineReader(f);
}

inline void execve(Str* argv0, List<Str*>* argv, Dict<Str*, Str*>* environ) {
  mylib::Str0 _argv0(argv0);

  int n = len(argv);
  // never deallocated
  char** _argv = static_cast<char**>(malloc(n + 1));

  // Annoying const_cast
  // https://stackoverflow.com/questions/190184/execv-and-const-ness
  for (int i = 0; i < n; ++i) {
    _argv[i] = const_cast<char*>(argv->index_(i)->data_);
  }
  _argv[n] = nullptr;

  int ret = ::execve(_argv0.Get(), _argv, nullptr);
  if (ret == -1) {
    throw new OSError(errno);
  }

  // NOTE(Jesse): ::execve() is specified to never return on success.  If we
  // hit this assertion, it returned successfully (or at least something other
  // than -1) but should have overwritten our address space with the invoked
  // process'
  InvalidCodePath();
}

}  // namespace posix

#endif  // POSIX_H
