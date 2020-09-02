// posix.h: Replacement for native/posixmodule.c

#ifndef POSIX_H
#define POSIX_H

#include <sys/wait.h>  // waitpid
#include <unistd.h>

#include "mylib.h"

// Save as a different name
#define X_OK_ X_OK
#define R_OK_ R_OK
#define W_OK_ W_OK
#define O_APPEND_ O_APPEND
#define O_CREAT_ O_CREAT
#define O_RDONLY_ O_RDONLY
#define O_RDWR_ O_RDWR
#define O_WRONLY_ O_WRONLY
#define O_TRUNC_ O_TRUNC

#undef X_OK
#undef R_OK
#undef W_OK
#undef O_APPEND
#undef O_CREAT
#undef O_RDONLY
#undef O_RDWR
#undef O_WRONLY
#undef O_TRUNC

namespace posix {

// aliases in this namespace
extern int X_OK;
extern int R_OK;
extern int W_OK;
extern int O_APPEND;
extern int O_CREAT;
extern int O_RDONLY;
extern int O_RDWR;
extern int O_WRONLY;
extern int O_TRUNC;

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
  // TODO: handle errno.  Although I'm not sure if it happens!
  return ::close(fd);
}

inline int putenv(Str* name, Str* value) {
  assert(0);
}

// TODO: errors
inline int chdir(Str* path) {
  assert(0);
}

inline int fork() {
  return ::fork();
}

inline void write(int fd, Str* value) {
  assert(0);
}

inline Tuple2<int, int> waitpid(int pid, int options) {
  int status;
  int result_pid = ::waitpid(pid, &status, options);
  return Tuple2<int, int>(result_pid, status);
}

// Can we use fcntl instead?
inline void dup2(int oldfd, int newfd) {
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

int open(Str* path, int mode, int perms);

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
    _argv[i] = const_cast<char*>(argv->index(i)->data_);
  }
  _argv[n] = nullptr;

  ::execve(_argv0.Get(), _argv, nullptr);
}

// Dummy exception posix::error
class error {};

}  // namespace posix

#endif  // POSIX_H
