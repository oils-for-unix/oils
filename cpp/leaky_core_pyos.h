// leaky_core_pyos.h: Replacement for core/pyos.py

#ifndef CORE_PYOS_H
#define CORE_PYOS_H

// clang-format off
#include "mycpp/myerror.h"
// clang-format on

#include <pwd.h>           // passwd
#include <sys/resource.h>  // getrusage
#include <sys/times.h>     // tms / times()
#include <sys/utsname.h>   // uname
#include <termios.h>

#include <cerrno>

#include "_build/cpp/syntax_asdl.h"
#include "leaky_time_.h"
#include "mycpp/mylib_leaky.h"
// has a member named errno.  That member can't be changed
// because it has to match the python error structure, which
// has an errno member.

namespace pyos {

const int TERM_ICANON = ICANON;
const int TERM_ECHO = ECHO;
const int EOF_SENTINEL = 256;
const int NEWLINE_CH = 10;

Tuple2<int, int> WaitPid();
Tuple2<int, int> Read(int fd, int n, List<Str*>* chunks);
Tuple2<int, int> ReadByte(int fd);
Str* ReadLine();
Dict<Str*, Str*>* Environ();
int Chdir(Str* dest_dir);
Str* GetMyHomeDir();
Str* GetHomeDir(Str* user_name);

class ReadError {
 public:
  ReadError(int err_num_) : err_num(err_num_) {
  }
  int err_num;
};

inline Str* GetUserName(int uid) {
  Str* result = kEmptyString;

  if (passwd* pw = getpwuid(uid)) {
    result = new Str(pw->pw_name);
  } else {
    throw new IOError(errno);
  }

  return result;
}

inline Str* OsType() {
  Str* result = kEmptyString;

  utsname un = {};
  if (::uname(&un) == 0) {
    result = new Str(un.sysname);
  } else {
    throw new IOError(errno);
  }

  return result;
}

inline Tuple3<double, double, double> Time() {
  rusage ru;  // NOTE(Jesse): Doesn't have to be cleared to 0.  The kernel
              // clears unused fields.
  if (::getrusage(RUSAGE_SELF, &ru) == -1) {
    throw new IOError(errno);
  }

  time_t t = time_::time();
  auto result = Tuple3<double, double, double>(
      (double)t, (double)ru.ru_utime.tv_sec, (double)ru.ru_stime.tv_sec);
  return result;
}

inline void PrintTimes() {
  tms t;
  if (times(&t) == -1) {
    throw new IOError(errno);
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

class TermState {
 public:
  TermState(int fd, int mask) {
    assert(0);
  }
  void Restore() {
    assert(0);
  }
};

inline bool InputAvailable(int fd) {
  assert(0);
}

void SignalState_AfterForkingChild();

class SignalState {
 public:
  SignalState() {
  }
  void InitShell() {
  }
  int last_sig_num = 0;

  DISALLOW_COPY_AND_ASSIGN(SignalState)
};

}  // namespace pyos

#endif  // CORE_PYOS_H
