// leaky_core.h: Replacement for core/*.py

#ifndef LEAKY_CORE_H
#define LEAKY_CORE_H

#include <termios.h>

#include "mycpp/runtime.h"

// Hacky forward declaration
namespace builtin_trap {
class _TrapHandler;
};

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

Str* GetUserName(int uid);
Str* OsType();
Tuple3<double, double, double> Time();
void PrintTimes();
bool InputAvailable(int fd);

class TermState {
 public:
  TermState(int fd, int mask) {
    assert(0);
  }
  void Restore() {
    assert(0);
  }
};

void SignalState_AfterForkingChild();

class SignalState {
 public:
  SignalState() {
  }
  void InitShell() {
  }
  void AddUserTrap(int sig_num, builtin_trap::_TrapHandler* handler) {
    NotImplemented();
  }
  void RemoveUserTrap(int sig_num) {
    NotImplemented();
  }
  int last_sig_num = 0;

  DISALLOW_COPY_AND_ASSIGN(SignalState)
};

}  // namespace pyos

class _OSError;  // declaration from mycpp/myerror.h

namespace pyutil {

bool IsValidCharEscape(int c);
Str* ChArrayToString(List<int>* ch_array);

class _ResourceLoader {
 public:
  virtual Str* Get(Str* path);
};

_ResourceLoader* GetResourceLoader();

void CopyFile(Str* in_path, Str* out_path);

Str* GetVersion(_ResourceLoader* loader);

Str* ShowAppVersion(Str* app_name, _ResourceLoader* loader);

Str* strerror(_OSError* e);

Str* BackslashEscape(Str* s, Str* meta_chars);

}  // namespace pyutil

#endif  // LEAKY_CORE_H
