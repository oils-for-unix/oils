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

// Make the signal queue slab 4096 bytes, including the GC header.  See
// cpp/core_test.cc.
const int kMaxSignalsInFlight = 1022;

class SignalSafe {
  // State that is shared between the main thread and signal handlers.
 public:
  SignalSafe()
      : GC_CLASS_FIXED(header_, field_mask(), sizeof(SignalSafe)),
        signal_queue_(AllocSignalQueue()),
        last_sig_num_(0),
        sigwinch_num_(UNTRAPPED_SIGWINCH),
        num_sigint_(0),
        num_dropped_(0) {
  }

  void UpdateFromSignalHandler(int sig_num) {
    DCHECK(signal_queue_ != nullptr);

    if (signal_queue_->len_ < signal_queue_->capacity_) {
      // We can append without allocating
      signal_queue_->append(sig_num);
    } else {
      // Unlikely: we would have to allocate.  Just increment a counter, which
      // we could expose this counter somewhere in the UI.
      num_dropped_++;
    }

    if (sig_num == SIGINT) {
      num_sigint_++;
    }
    if (sig_num == SIGWINCH) {
      sig_num = sigwinch_num_;
    }
    last_sig_num_ = sig_num;
  }

  // Main thread takes signals so it can run traps.
  List<int>* TakeSignalQueue() {
    // TODO: Consider using 2 List<int> and swapping them.

    List<int>* new_queue = AllocSignalQueue();
    List<int>* ret = signal_queue_;
    signal_queue_ = new_queue;
    return ret;
  }

  // Main thread tells us whether SIGWINCH is trapped.
  void SetSigWinchCode(int code) {
    sigwinch_num_ = code;
  }

  // Main thread wants to get the last signal received.
  int LastSignal() {
    return last_sig_num_;
  }

  // Main thread wants to know if SIGINT received since the last time
  // PollSigInt was called.
  bool PollSigInt() {
    bool result = num_sigint_ > 0;

    num_sigint_ = 0;  // Reset counter

    return result;
  }

  static constexpr uint16_t field_mask() {
    return maskbit(offsetof(SignalSafe, signal_queue_));
  }

  GC_OBJ(header_);
  List<int>* signal_queue_;  // public for testing

 private:
  // Enforcing private state because two different threads will use it!

  List<int>* AllocSignalQueue() {
    // Reserve a fixed number of signals.  We never allocate in Update().
    List<int>* ret = NewList<int>();
    ret->reserve(kMaxSignalsInFlight);
    return ret;
  }

  int last_sig_num_;
  int sigwinch_num_;
  int num_sigint_;
  int num_dropped_;
};

extern SignalSafe* gSignalSafe;

// Allocate global and return it.
SignalSafe* InitSignalSafe();

void Sigaction(int sig_num, sighandler_t handler);

void RegisterSignalInterest(int sig_num);

Tuple2<Str*, int>* MakeDirCacheKey(Str* path);

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

void ShowAppVersion(_ResourceLoader* loader);

Str* strerror(IOError_OSError* e);

Str* BackslashEscape(Str* s, Str* meta_chars);

grammar::Grammar* LoadOilGrammar(_ResourceLoader*);

}  // namespace pyutil

#endif  // LEAKY_CORE_H
