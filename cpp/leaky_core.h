// leaky_core.h: Replacement for core/*.py

#ifndef LEAKY_CORE_H
#define LEAKY_CORE_H

#include <signal.h>
#include <termios.h>

#include "_gen/frontend/syntax.asdl.h"
#include "mycpp/runtime.h"

namespace comp_ui {
class _IDisplay;
}  // namespace comp_ui

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
  explicit ReadError(int err_num_) : err_num(err_num_) {
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

// An abstract type that approximates python's Callable-based signal().
class SignalHandler : public Obj {
 public:
  // XXX: This will probably break the garbage collector. We may need to rework
  // this when it gets enabled.
  SignalHandler() : Obj(Tag::FixedSize, kZeroMask, 0) {
  }
  virtual void Run(int) = 0;
};

void Sigaction(int sig_num, SignalHandler* handler);
void Sigaction(int sig_num, sighandler_t handler);

void ReserveHandlerCapacity(List<syntax_asdl::command_t*>* list);

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
