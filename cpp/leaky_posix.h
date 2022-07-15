// leaky_posix.h: Replacement for native/posixmodule.c

#ifndef POSIX_H
#define POSIX_H

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

  int n_args = len(argv);
  // never deallocated
  char** _argv = static_cast<char**>(malloc((n_args + 1) * sizeof(char*)));

  // Annoying const_cast
  // https://stackoverflow.com/questions/190184/execv-and-const-ness
  for (int i = 0; i < n_args; ++i) {
    _argv[i] = const_cast<char*>(argv->index_(i)->data_);
  }
  _argv[n_args] = nullptr;

  // Convert environ into an array of pointers to strings of the form: "k=v".
  int n_env = len(environ);
  char** envp = static_cast<char**>(malloc((n_env + 1) * sizeof(char*)));
  int i = 0;
  for (const auto& kv : environ->items_) {
    Str* k = kv.first;
    Str* v = kv.second;
    int joined_len = k->len_ + v->len_ + 1;
    char* buf = static_cast<char*>(malloc(joined_len + 1));
    memcpy(buf, k->data_, k->len_);
    buf[k->len_] = '=';
    memcpy(buf + k->len_ + 1, v->data_, v->len_);
    buf[joined_len] = '\0';
    envp[i++] = buf;
  }
  envp[n_env] = nullptr;

  int ret = ::execve(_argv0.Get(), _argv, envp);
  if (ret == -1) {
    throw IOError(errno);
  }

  // NOTE(Jesse): ::execve() is specified to never return on success.  If we
  // hit this assertion, it returned successfully (or at least something other
  // than -1) but should have overwritten our address space with the invoked
  // process'
  InvalidCodePath();
}

}  // namespace posix

#endif  // POSIX_H
