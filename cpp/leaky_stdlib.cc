// leaky_stdlib.cc: Replacement for standard library modules
// and native/posixmodule.c

#include "leaky_stdlib.h"

#include <errno.h>
#include <fcntl.h>      // open
#include <signal.h>     // kill
#include <sys/stat.h>   // umask
#include <sys/types.h>  // umask
#include <sys/wait.h>   // WUNTRACED
#include <time.h>
#include <unistd.h>

#include "cpp/leaky_core_error.h"
#include "cpp/leaky_core_pyerror.h"
#include "mycpp/runtime.h"

namespace fcntl_ {

int fcntl(int fd, int cmd) {
  int result = ::fcntl(fd, cmd);
  if (result < 0) {
    throw Alloc<IOError>(errno);
  }
  return result;
}

int fcntl(int fd, int cmd, int arg) {
  int result = ::fcntl(fd, cmd, arg);
  if (result < 0) {
    throw Alloc<IOError>(errno);
  }
  return result;
}

}  // namespace fcntl_

namespace posix {

mode_t umask(mode_t mask) {
  return ::umask(mask);
}

int open(Str* path, int flags, int perms) {
  return ::open(path->data_, flags, perms);
}

void dup2(int oldfd, int newfd) {
  if (::dup2(oldfd, newfd) < 0) {
    throw Alloc<OSError>(errno);
  }
}
void putenv(Str* name, Str* value) {
  int overwrite = 1;
  int ret = ::setenv(name->data_, value->data_, overwrite);
  if (ret < 0) {
    throw Alloc<IOError>(errno);
  }
}

mylib::LineReader* fdopen(int fd, Str* c_mode) {
  FILE* f = ::fdopen(fd, c_mode->data_);

  // TODO: raise exception
  assert(f);

  return Alloc<mylib::CFileLineReader>(f);
}

void execve(Str* argv0, List<Str*>* argv, Dict<Str*, Str*>* environ) {
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

  int env_index = 0;
  for (DictIter<Str*, Str*> it(environ); !it.Done(); it.Next()) {
    Str* k = it.Key();
    Str* v = it.Value();

    int joined_len = len(k) + len(v) + 1;
    char* buf = static_cast<char*>(malloc(joined_len + 1));
    memcpy(buf, k->data_, len(k));
    buf[len(k)] = '=';
    memcpy(buf + len(k) + 1, v->data_, len(v));
    buf[joined_len] = '\0';

    envp[env_index++] = buf;
  }
  envp[n_env] = nullptr;

  int ret = ::execve(argv0->data_, _argv, envp);
  if (ret == -1) {
    throw Alloc<OSError>(errno);
  }

  // NOTE(Jesse): ::execve() is specified to never return on success.  If we
  // hit this assertion, it returned successfully (or at least something other
  // than -1) but should have overwritten our address space with the invoked
  // process'
  InvalidCodePath();
}

void kill(int pid, int sig) {
  if (::kill(pid, sig) != 0) {
    throw Alloc<OSError>(errno);
  }
}

}  // namespace posix

namespace time_ {

void tzset() {
  ::tzset();
}

time_t time() {
  return ::time(nullptr);
}

// NOTE(Jesse): time_t is specified to be an arithmetic type by C++. On most
// systems it's a 64-bit integer.  64 bits is used because 32 will overflow in
// 2038.  Someone on a comittee somewhere thought of that when moving to 64-bit
// architectures to prevent breaking ABI again; on 32-bit systems it's usually
// 32 bits.  Point being, using anything but the time_t typedef here could
// (unlikely, but possible) produce weird behavior.
time_t localtime(time_t ts) {
  tm* loc_time = ::localtime(&ts);
  time_t result = mktime(loc_time);
  return result;
}

Str* strftime(Str* s, time_t ts) {
  // TODO: may not work with leaky_containers.h
  // https://github.com/oilshell/oil/issues/1221
  tm* loc_time = ::localtime(&ts);

  const int max_len = 1024;
  Str* result = OverAllocatedStr(max_len);
  int n = strftime(result->data(), max_len, s->data_, loc_time);
  if (n == 0) {
    // bash silently truncates on large format string like
    //   printf '%(%Y)T'
    // Oil doesn't mask errors
    // No error location info, but leaving it out points reliably to 'printf'
    e_die(StrFromC("strftime() result exceeds 1024 bytes"));
  }
  result->SetObjLenFromStrLen(n);
  return result;
}

}  // namespace time_
