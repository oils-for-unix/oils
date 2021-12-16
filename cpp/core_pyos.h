// core_pyos.h: Replacement for core/pyos.py

#ifndef CORE_PYOS_H
#define CORE_PYOS_H

#include <termios.h>

#include "mylib.h"
#include "syntax_asdl.h"

namespace pyos {

const int TERM_ICANON = ICANON;
const int TERM_ECHO = ECHO;
const int EOF_SENTINEL = 256;
const int NEWLINE_CH = 10;

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
  assert(0);
}

inline Str* OsType() {
  // uname()[0].lower()
  return new Str("TODO");
}

inline Tuple3<double, double, double> Time() {
  assert(0);
}

inline void PrintTimes() {
  assert(0);
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
