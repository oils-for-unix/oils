// core_pyos.cc

#include "core_pyos.h"  // undefined errno
#include <errno.h>
#include <pwd.h>
#include <signal.h>
#include <unistd.h>  // getuid(), environ

static Str* CopyStr(const char* s) {
  int n = strlen(s);
  char* buf = static_cast<char*>(malloc(n + 1));
  strcpy(buf, s);  // includes NUL terminator

  return new Str(s, n);
}

namespace pyos {

Tuple2<int, int> Read(int fd, int n, List<Str*>* chunks) {
  assert(0);
}

Tuple2<int, int> ReadByte(int fd) {
  unsigned char buf[1];
  ssize_t n = read(fd, &buf, 1);
  if (n < 0) {  // read error
    return Tuple2<int, int>(-1, errno);
  } else if (n == 0) {  // EOF
    return Tuple2<int, int>(EOF_SENTINEL, 0);
  } else {  // return character
    return Tuple2<int, int>(buf[0], 0);
  }
}

// for read --line
Str* ReadLine() {
  assert(0);
}

Dict<Str*, Str*>* Environ() {
  auto d = new Dict<Str*, Str*>();

  for (char** env = environ; *env; ++env) {
    char* pair = *env;

    char* eq = strchr(pair, '=');
    assert(eq != nullptr);  // must look like KEY=value

    int key_len = eq - pair;
    char* buf = static_cast<char*>(malloc(key_len + 1));
    memcpy(buf, pair, key_len);  // includes NUL terminator
    buf[key_len] = '\0';

    Str* key = new Str(buf, key_len);

    int len = strlen(pair);
    int val_len = len - key_len - 1;
    char* buf2 = static_cast<char*>(malloc(val_len + 1));
    memcpy(buf2, eq + 1, val_len);  // copy starting after =
    buf2[val_len] = '\0';

    Str* val = new Str(buf2, val_len);

    d->set(key, val);
  }

  return d;
}

int Chdir(Str* dest_dir) {
  mylib::Str0 d(dest_dir);
  if (chdir(d.Get()) == 0) {
    return 0;  // success
  } else {
    return errno;
  }
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
