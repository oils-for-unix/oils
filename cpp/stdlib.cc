// stdlib.cc: Replacement for standard library modules
// and native/posixmodule.c

#include "stdlib.h"

#include <dirent.h>  // closedir(), opendir(), readdir()
#include <errno.h>
#include <fcntl.h>      // open
#include <signal.h>     // kill
#include <sys/stat.h>   // umask
#include <sys/types.h>  // umask
#include <sys/wait.h>   // WUNTRACED
#include <time.h>
#include <unistd.h>

#include "cpp/core_error.h"
#include "cpp/core_pyerror.h"  // e_die for strftime
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
  // No error case: always succeeds
  return ::umask(mask);
}

int open(Str* path, int flags, int perms) {
  int result = ::open(path->data_, flags, perms);
  if (result < 0) {
    throw Alloc<OSError>(errno);
  }
  return result;
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

  // ::execve() never returns on succcess
  FAIL(kShouldNotGetHere);
}

void kill(int pid, int sig) {
  if (::kill(pid, sig) != 0) {
    throw Alloc<OSError>(errno);
  }
}

List<Str*>* listdir(Str* path) {
  DIR* dirp = opendir(path->data());
  if (dirp == NULL) {
    throw Alloc<OSError>(errno);
  }

  auto* ret = NewList<Str*>();
  while (true) {
    errno = 0;
    struct dirent* ep = readdir(dirp);
    if (ep == NULL) {
      if (errno == 0) {
        break;
      } else {
        closedir(dirp);
        throw Alloc<OSError>(errno);
      }
    }
    int name_len = strlen(ep->d_name);
    if (ep->d_name[0] == '.' &&
        (name_len == 1 || (ep->d_name[1] == '.' && name_len == 2))) {
      continue;
    }
    ret->append(StrFromC(ep->d_name, name_len));
  }

  closedir(dirp);

  return ret;
}

}  // namespace posix

namespace time_ {

void tzset() {
  // No error case: no return value
  ::tzset();
}

time_t time() {
  time_t result = ::time(nullptr);
  if (result < 0) {
    throw Alloc<IOError>(errno);
  }
  return result;
}

// NOTE(Jesse): time_t is specified to be an arithmetic type by C++. On most
// systems it's a 64-bit integer.  64 bits is used because 32 will overflow in
// 2038.  Someone on a comittee somewhere thought of that when moving to
// 64-bit architectures to prevent breaking ABI again; on 32-bit systems it's
// usually 32 bits.  Point being, using anything but the time_t typedef here
// could (unlikely, but possible) produce weird behavior.
time_t localtime(time_t ts) {
  // localtime returns a pointer to a static buffer
  tm* loc_time = ::localtime(&ts);

  time_t result = mktime(loc_time);
  if (result < 0) {
    throw Alloc<IOError>(errno);
  }
  return result;
}

Str* strftime(Str* s, time_t ts) {
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
  result->MaybeShrink(n);
  return result;
}

void sleep(int seconds) {
  ::sleep(seconds);
}

}  // namespace time_
