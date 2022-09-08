// leaky_core.cc

// clang-format off
#include "mycpp/myerror.h"
// clang-format on

#include "cpp/leaky_core.h"

#include <errno.h>
#include <pwd.h>  // passwd
#include <signal.h>
#include <sys/resource.h>  // getrusage
#include <sys/times.h>     // tms / times()
#include <sys/utsname.h>   // uname
#include <sys/wait.h>      // waitpid()
#include <time.h>          // time()
#include <unistd.h>        // getuid(), environ

namespace pyos {

Tuple2<int, int> WaitPid() {
  int status;
  int result = ::waitpid(-1, &status, WUNTRACED);
  if (result < 0) {
    return Tuple2<int, int>(-1, errno);
  }
  return Tuple2<int, int>(result, status);
}

Tuple2<int, int> Read(int fd, int n, List<Str*>* chunks) {
  Str* s = OverAllocatedStr(n);  // Allocate enough for the result

  int length = ::read(fd, s->data(), n);
  if (length < 0) {
    return Tuple2<int, int>(-1, errno);
  }
  if (length == 0) {
    return Tuple2<int, int>(length, 0);
  }

  // Now we know how much data we got back
  s->SetObjLenFromStrLen(length);
  chunks->append(s);

  return Tuple2<int, int>(length, 0);
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
  assert(0);  // Does this get called?
}

Dict<Str*, Str*>* Environ() {
  auto d = NewDict<Str*, Str*>();

  for (char** env = environ; *env; ++env) {
    char* pair = *env;

    char* eq = strchr(pair, '=');
    assert(eq != nullptr);  // must look like KEY=value

    int key_len = eq - pair;
    char* buf = static_cast<char*>(malloc(key_len + 1));
    memcpy(buf, pair, key_len);  // includes NUL terminator
    buf[key_len] = '\0';

    Str* key = StrFromC(buf, key_len);

    int len = strlen(pair);
    int val_len = len - key_len - 1;
    char* buf2 = static_cast<char*>(malloc(val_len + 1));
    memcpy(buf2, eq + 1, val_len);  // copy starting after =
    buf2[val_len] = '\0';

    Str* val = StrFromC(buf2, val_len);

    d->set(key, val);
  }

  return d;
}

int Chdir(Str* dest_dir) {
  if (chdir(dest_dir->data_) == 0) {
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
  return StrFromC(entry->pw_dir);
}

Str* GetHomeDir(Str* user_name) {
  // Don't free this.  (May return a pointer to a static area)
  struct passwd* entry = getpwnam(user_name->data_);
  if (entry == nullptr) {
    return nullptr;
  }
  return StrFromC(entry->pw_dir);
}

Str* GetUserName(int uid) {
  Str* result = kEmptyString;

  if (passwd* pw = getpwuid(uid)) {
    result = CopyBufferIntoNewStr(pw->pw_name);
  } else {
    throw Alloc<IOError>(errno);
  }

  return result;
}

Str* OsType() {
  Str* result = kEmptyString;

  utsname un = {};
  if (::uname(&un) == 0) {
    result = CopyBufferIntoNewStr(un.sysname);
  } else {
    throw Alloc<IOError>(errno);
  }

  return result;
}

Tuple3<double, double, double> Time() {
  rusage ru;  // NOTE(Jesse): Doesn't have to be cleared to 0.  The kernel
              // clears unused fields.
  if (::getrusage(RUSAGE_SELF, &ru) == -1) {
    throw Alloc<IOError>(errno);
  }

  time_t t = ::time(nullptr);
  auto result = Tuple3<double, double, double>(
      static_cast<double>(t), static_cast<double>(ru.ru_utime.tv_sec),
      static_cast<double>(ru.ru_stime.tv_sec));
  return result;
}

void PrintTimes() {
  tms t;
  if (times(&t) == -1) {
    throw Alloc<IOError>(errno);
  } else {
    {
      int user_minutes = t.tms_utime / 60;
      float user_seconds = t.tms_utime % 60;
      int system_minutes = t.tms_stime / 60;
      float system_seconds = t.tms_stime % 60;
      printf("%dm%1.3fs %dm%1.3fs", user_minutes, user_seconds, system_minutes,
             system_seconds);
    }

    {
      int child_user_minutes = t.tms_cutime / 60;
      float child_user_seconds = t.tms_cutime % 60;
      int child_system_minutes = t.tms_cstime / 60;
      float child_system_seconds = t.tms_cstime % 60;
      printf("%dm%1.3fs %dm%1.3fs", child_user_minutes, child_user_seconds,
             child_system_minutes, child_system_seconds);
    }
  }
}

bool InputAvailable(int fd) {
  NotImplemented();
}

void SignalState_AfterForkingChild() {
  signal(SIGQUIT, SIG_DFL);
  signal(SIGPIPE, SIG_DFL);
  signal(SIGTSTP, SIG_DFL);
}

}  // namespace pyos

namespace pyutil {

bool IsValidCharEscape(int c) {
  if (c == '/' || c == '.' || c == '-') {
    return false;
  }
  if (c == ' ') {  // foo\ bar is idiomatic
    return true;
  }
  return ispunct(c);
}

Str* ChArrayToString(List<int>* ch_array) {
  int n = len(ch_array);
  unsigned char* buf = static_cast<unsigned char*>(malloc(n + 1));
  for (int i = 0; i < n; ++i) {
    buf[i] = ch_array->index_(i);
  }
  buf[n] = '\0';
  return CopyBufferIntoNewStr(reinterpret_cast<char*>(buf), n);
}

Str* _ResourceLoader::Get(Str* path) {
  /* NotImplemented(); */
  return StrFromC("TODO");
}

_ResourceLoader* GetResourceLoader() {
  return Alloc<_ResourceLoader>();
}

void CopyFile(Str* in_path, Str* out_path) {
  assert(0);
}

Str* GetVersion(_ResourceLoader* loader) {
  /* NotImplemented(); */
  return StrFromC("TODO");
}

Str* ShowAppVersion(Str* app_name, _ResourceLoader* loader) {
  assert(0);
}

Str* BackslashEscape(Str* s, Str* meta_chars) {
  int upper_bound = len(s) * 2;
  char* buf = static_cast<char*>(malloc(upper_bound));
  char* p = buf;

  for (int i = 0; i < len(s); ++i) {
    char c = s->data_[i];
    if (memchr(meta_chars->data_, c, len(meta_chars))) {
      *p++ = '\\';
    }
    *p++ = c;
  }
  int len = p - buf;
  return CopyBufferIntoNewStr(buf, len);
}

// Hack so e->errno will work below
#undef errno

Str* strerror(_OSError* e) {
  return CopyBufferIntoNewStr(::strerror(e->errno));
}

}  // namespace pyutil
