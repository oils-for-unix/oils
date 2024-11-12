// gc_iolib.h - corresponds to mycpp/iolib.py

#ifndef MYCPP_GC_IOLIB_H
#define MYCPP_GC_IOLIB_H

// For now, we assume that simple int and pointer operations are atomic, rather
// than using std::atomic.  Could be a ./configure option later.
//
// See doc/portability.md.

#define LOCK_FREE_ATOMICS 0

#if LOCK_FREE_ATOMICS
  #include <atomic>
#endif
#include <signal.h>

#include "mycpp/gc_list.h"

namespace iolib {

const int UNTRAPPED_SIGWINCH = -1;

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

  void SetSigIntTrapped(bool b) {
    sigint_trapped_ = b;
  }

  // Used by pyos.WaitPid, Read, ReadByte.
  bool PollSigInt() {
    bool result = received_sigint_;
    received_sigint_ = false;
    return result;
  }

  // Used by osh/cmd_eval.py.  Main loop wants to know if SIGINT was received
  // since the last time PollSigInt was called.
  bool PollUntrappedSigInt() {
    bool received = PollSigInt();  // clears a flag
    return received && !sigint_trapped_;
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

  bool sigint_trapped_;
  int received_sigint_;
  int received_sigwinch_;
  int sigwinch_code_;
  int num_dropped_;
};

extern SignalSafe* gSignalSafe;

// Allocate global and return it.
SignalSafe* InitSignalSafe();

void RegisterSignalInterest(int sig_num);

void sigaction(int sig_num, void (*handler)(int));

}  // namespace iolib

#endif  // MYCPP_GC_IOLIB_H
