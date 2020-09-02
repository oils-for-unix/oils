// core_pyos.cc

#include "core_pyos.h"  // undefined errno
#include <errno.h>
#include <pwd.h>
#include <signal.h>
#include <unistd.h>  // getuid()

static Str* CopyStr(const char* s) {
  int n = strlen(s);
  char* buf = static_cast<char*>(malloc(n + 1));
  strcpy(buf, s);  // includes NUL terminator

  return new Str(s, n);
}

namespace pyos {

int Chdir(Str* dest_dir) {
  errno = 0;
  mylib::Str0 d(dest_dir);
  chdir(d.Get());
  return errno;
}

Str* GetMyHomeDir() {
  uid_t uid = getuid();  // always succeeds

  // Don't free this.  (May return a pointer to a static area)
  struct passwd* entry = getpwuid(uid);
  if (entry == nullptr) {
    return nullptr;
  }
  return CopyStr(entry->pw_dir);
}

Str* GetHomeDir(Str* user_name) {
  mylib::Str0 user_name0(user_name);

  // Don't free this.  (May return a pointer to a static area)
  struct passwd* entry = getpwnam(user_name0.Get());
  if (entry == nullptr) {
    return nullptr;
  }
  return CopyStr(entry->pw_dir);
}

void SignalState_AfterForkingChild() {
  signal(SIGQUIT, SIG_DFL);
  signal(SIGPIPE, SIG_DFL);
  signal(SIGTSTP, SIG_DFL);
}

}  // namespace pyos
