// core.h: Replacement for core/*.py

#ifndef LEAKY_CORE_H
#define LEAKY_CORE_H

#include <pwd.h>     // passwd
#include <signal.h>  // sighandler_t
#include <termios.h>

#include "_gen/frontend/syntax.asdl.h"
#include "cpp/pgen2.h"
#include "mycpp/runtime.h"

// Hacky forward declaration
namespace completion {
class RootCompleter;
};

namespace pyos {

const int TERM_ICANON = ICANON;
const int TERM_ECHO = ECHO;
const int EOF_SENTINEL = 256;
const int NEWLINE_CH = 10;
const int UNTRAPPED_SIGWINCH = -1;
const int kMaxSignalsInFlight = 1024;

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
  explicit ReadError(int err_num_)
      : GC_CLASS_FIXED(header_, kZeroMask, sizeof(ReadError)),
        err_num(err_num_) {
  }

  GC_OBJ(header_);
  int err_num;
};

class PasswdEntry {
 public:
  explicit PasswdEntry(const passwd* entry)
      : GC_CLASS_FIXED(header_, field_mask(), sizeof(PasswdEntry)),
        pw_name(StrFromC(entry->pw_name)),
        pw_uid(entry->pw_uid),
        pw_gid(entry->pw_gid) {
  }

  GC_OBJ(header_);
  Str* pw_name;
  int pw_uid;
  int pw_gid;

  static constexpr uint16_t field_mask() {
    return maskbit(offsetof(PasswdEntry, pw_name));
  }
};

List<PasswdEntry*>* GetAllUsers();

Str* GetUserName(int uid);

Str* OsType();

Tuple3<double, double, double> Time();

void PrintTimes();

bool InputAvailable(int fd);

inline void FlushStdout() {
  // Flush libc buffers
  fflush(stdout);
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

class SignalHandler {
 public:
  SignalHandler()
      : GC_CLASS_FIXED(header_, field_mask(), sizeof(SignalHandler)),
        signal_queue_(nullptr),
        last_sig_num_(0),
        sigwinch_num_(UNTRAPPED_SIGWINCH) {
  }

  void Update(int sig_num);
  List<int>* TakeSignalQueue();

  GC_OBJ(header_);
  List<int>* signal_queue_;
  int last_sig_num_;
  int sigwinch_num_;

  static constexpr uint16_t field_mask() {
    return maskbit(offsetof(SignalHandler, signal_queue_));
  }
};

void Sigaction(int sig_num, sighandler_t handler);

void RegisterSignalInterest(int sig_num);

List<int>* TakeSignalQueue();

int LastSignal();

void SetSigwinchCode(int code);

void InitShell();

Tuple2<Str*, int> MakeDirCacheKey(Str* path);

}  // namespace pyos

namespace pyutil {

bool IsValidCharEscape(Str* c);
Str* ChArrayToString(List<int>* ch_array);

class _ResourceLoader {
 public:
  _ResourceLoader()
      : GC_CLASS_FIXED(header_, kZeroMask, sizeof(_ResourceLoader)) {
  }

  virtual Str* Get(Str* path);

  GC_OBJ(header_);
};

_ResourceLoader* GetResourceLoader();

Str* GetVersion(_ResourceLoader* loader);

Str* ShowAppVersion(Str* app_name, _ResourceLoader* loader);

Str* strerror(IOError_OSError* e);

Str* BackslashEscape(Str* s, Str* meta_chars);

grammar::Grammar* LoadOilGrammar(_ResourceLoader*);

}  // namespace pyutil

#endif  // LEAKY_CORE_H
