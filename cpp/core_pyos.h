// core_pyos.h: Replacement for core/pyos.py

#ifndef CORE_PYOS_H
#define CORE_PYOS_H

#include "mylib.h"
#include "syntax_asdl.h"

namespace pyos {

inline Str* GetMyHomeDir() {
  assert(0);
}

inline Str* GetHomeDir(syntax_asdl::Token* token) {
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

inline Str* ReadBytesFromTerminal(int fd, int n) {
  assert(0);
}

}  // namespace pyos

#endif  // CORE_PYOS_H
