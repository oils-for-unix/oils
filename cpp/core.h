// core.h: Replacement for core/*.py

#ifndef LEAKY_CORE_H
#define LEAKY_CORE_H

#include <pwd.h>  // passwd
#include <signal.h>
#include <termios.h>

// For now, we assume that simple int and pointer operations are atomic, rather
// than using std::atomic.  Could be a ./configure option later.
//
// See doc/portability.md.

#define LOCK_FREE_ATOMICS 0

#if LOCK_FREE_ATOMICS
  #include <atomic>
#endif

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

Tuple2<int, int> WaitPid(int waitpid_options);
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

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(kZeroMask, sizeof(ReadError));
  }

  int err_num;
};

class PasswdEntry {
 public:
  explicit PasswdEntry(const passwd* entry)
      : pw_name(StrFromC(entry->pw_name)),
        pw_uid(entry->pw_uid),
        pw_gid(entry->pw_gid) {
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(PasswdEntry));
  }

  Str* pw_name;
  int pw_uid;
  int pw_gid;

  static constexpr uint32_t field_mask() {
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

Tuple2<int, void*> PushTermAttrs(int fd, int mask);
void PopTermAttrs(int fd, int orig_local_modes, void* term_attrs);

// Make the signal queue slab 4096 bytes, including the GC header.  See
// cpp/core_test.cc.
const int kMaxPendingSignals = 1022;

class SignalSafe {
  // State that is shared between the main thread and signal handlers.
 public:
  SignalSafe()
      : pending_signals_(AllocSignalList()),
        empty_list_(AllocSignalList()),  // to avoid repeated allocation
        last_sig_num_(0),
        received_sigint_(false),
        received_sigwinch_(false),
        sigwinch_code_(UNTRAPPED_SIGWINCH),
        num_dropped_(0) {
  }

  // Called from signal handling context.  Do not allocate.
  void UpdateFromSignalHandler(int sig_num) {
    if (pending_signals_->len_ < pending_signals_->capacity_) {
      // We can append without allocating
      pending_signals_->append(sig_num);
    } else {
      // Unlikely: we would have to allocate.  Just increment a counter, which
      // we could expose somewhere in the UI.
      num_dropped_++;
    }

    if (sig_num == SIGINT) {
      received_sigint_ = true;
    }

    if (sig_num == SIGWINCH) {
      received_sigwinch_ = true;
      sig_num = sigwinch_code_;  // mutate param
    }

#if LOCK_FREE_ATOMICS
    last_sig_num_.store(sig_num);
#else
    last_sig_num_ = sig_num;
#endif
  }

  // Main thread takes signals so it can run traps.
  List<int>* TakePendingSignals() {
    List<int>* ret = pending_signals_;

    // Make sure we have a distinct list to reuse.
    DCHECK(empty_list_ != pending_signals_);
    pending_signals_ = empty_list_;

    return ret;
  }

  // Main thread returns the same list as an optimization to avoid allocation.
  void ReuseEmptyList(List<int>* empty_list) {
    DCHECK(empty_list != pending_signals_);  // must be different
    DCHECK(len(empty_list) == 0);            // main thread clears
    DCHECK(empty_list->capacity_ == kMaxPendingSignals);

    empty_list_ = empty_list;
  }

  // Main thread wants to get the last signal received.
  int LastSignal() {
#if LOCK_FREE_ATOMICS
    return last_sig_num_.load();
#else
    return last_sig_num_;
#endif
  }

  // Main thread wants to know if SIGINT was received since the last time
  // PollSigInt was called.
  bool PollSigInt() {
    bool result = received_sigint_;
    received_sigint_ = false;
    return result;
  }

  // Main thread tells us whether SIGWINCH is trapped.
  void SetSigWinchCode(int code) {
    sigwinch_code_ = code;
  }

  // Main thread wants to know if SIGWINCH was received since the last time
  // PollSigWinch was called.
  bool PollSigWinch() {
    bool result = received_sigwinch_;
    received_sigwinch_ = false;
    return result;
  }

  static constexpr uint32_t field_mask() {
    return maskbit(offsetof(SignalSafe, pending_signals_)) |
           maskbit(offsetof(SignalSafe, empty_list_));
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(SignalSafe));
  }

  List<int>* pending_signals_;  // public for testing
  List<int>* empty_list_;

 private:
  // Enforce private state because two different "threads" will use it!

  // Reserve a fixed number of signals.
  List<int>* AllocSignalList() {
    List<int>* ret = NewList<int>();
    ret->reserve(kMaxPendingSignals);
    return ret;
  }

#if LOCK_FREE_ATOMICS
  std::atomic<int> last_sig_num_;
#else
  int last_sig_num_;
#endif
  // Not sufficient: volatile sig_atomic_t last_sig_num_;

  int received_sigint_;
  int received_sigwinch_;
  int sigwinch_code_;
  int num_dropped_;
};

extern SignalSafe* gSignalSafe;

// Allocate global and return it.
SignalSafe* InitSignalSafe();

void Sigaction(int sig_num, void (*handler)(int));

void RegisterSignalInterest(int sig_num);

Tuple2<Str*, int>* MakeDirCacheKey(Str* path);

}  // namespace pyos

namespace pyutil {

bool IsValidCharEscape(Str* c);
Str* ChArrayToString(List<int>* ch_array);

class _ResourceLoader {
 public:
  _ResourceLoader() {
  }

  virtual Str* Get(Str* path);

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(kZeroMask, sizeof(_ResourceLoader));
  }
};

_ResourceLoader* GetResourceLoader();

Str* GetVersion(_ResourceLoader* loader);

void PrintVersionDetails(_ResourceLoader* loader);

Str* strerror(IOError_OSError* e);

Str* BackslashEscape(Str* s, Str* meta_chars);

grammar::Grammar* LoadOilGrammar(_ResourceLoader*);

}  // namespace pyutil

#endif  // LEAKY_CORE_H
