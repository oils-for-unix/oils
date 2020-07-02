// core_pyos.h: Replacement for core/pyos.py

#ifndef CORE_PYOS_H
#define CORE_PYOS_H

#include <termios.h>
#include "mylib.h"
#include "syntax_asdl.h"

namespace pyos {

const int TERM_ICANON = ICANON;
const int TERM_ECHO = ECHO;

inline Str* GetMyHomeDir() {
  assert(0);
}

inline Str* GetHomeDir(Str* user_name) {
  assert(0);
}

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

}  // namespace pyos

#endif  // CORE_PYOS_H
