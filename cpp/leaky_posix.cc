// posix.cc: Replacement for native/posixmodule.c

// clang-format off
#include "mycpp/myerror.h"  // for OSError; must come first
// clang-format on

#include "leaky_posix.h"

#include <errno.h>
#include <fcntl.h>      // open
#include <sys/stat.h>   // umask
#include <sys/types.h>  // umask
#include <sys/wait.h>   // WUNTRACED
#include <unistd.h>

namespace posix {

int umask(int mask) {
  // note: assuming mode_t fits in an int
  return ::umask(mask);
}

int open(Str* path, int flags, int perms) {
  mylib::Str0 path0(path);
  return ::open(path0.Get(), flags, perms);
}

void dup2(int oldfd, int newfd) {
  if (::dup2(oldfd, newfd) < 0) {
    throw new OSError(errno);
  }
}
void putenv(Str* name, Str* value) {
  assert(name->IsNulTerminated());
  assert(value->IsNulTerminated());
  int overwrite = 1;
  int ret = ::setenv(name->data_, value->data_, overwrite);
  if (ret < 0) {
    throw new IOError(errno);
  }
}

mylib::LineReader* fdopen(int fd, Str* c_mode) {
  mylib::Str0 c_mode0(c_mode);
  FILE* f = ::fdopen(fd, c_mode0.Get());

  // TODO: raise exception
  assert(f);

  return new mylib::CFileLineReader(f);
}

void execve(Str* argv0, List<Str*>* argv, Dict<Str*, Str*>* environ) {
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
    throw new OSError(errno);
  }

  // NOTE(Jesse): ::execve() is specified to never return on success.  If we
  // hit this assertion, it returned successfully (or at least something other
  // than -1) but should have overwritten our address space with the invoked
  // process'
  InvalidCodePath();
}

}  // namespace posix
