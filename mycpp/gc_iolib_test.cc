#include "mycpp/gc_iolib.h"

#include <unistd.h>

#include "mycpp/gc_alloc.h"  // gHeap
#include "vendor/greatest.h"

TEST signal_test() {
  iolib::SignalSafe* signal_safe = iolib::InitSignalSafe();

  {
    List<int>* q = signal_safe->TakePendingSignals();
    ASSERT(q != nullptr);
    ASSERT_EQ(0, len(q));
    signal_safe->ReuseEmptyList(q);
  }

  pid_t mypid = getpid();

  iolib::RegisterSignalInterest(SIGUSR1);
  iolib::RegisterSignalInterest(SIGUSR2);

  kill(mypid, SIGUSR1);
  ASSERT_EQ(SIGUSR1, signal_safe->LastSignal());

  kill(mypid, SIGUSR2);
  ASSERT_EQ(SIGUSR2, signal_safe->LastSignal());

  {
    List<int>* q = signal_safe->TakePendingSignals();
    ASSERT(q != nullptr);
    ASSERT_EQ(2, len(q));
    ASSERT_EQ(SIGUSR1, q->at(0));
    ASSERT_EQ(SIGUSR2, q->at(1));

    q->clear();
    signal_safe->ReuseEmptyList(q);
  }

  iolib::sigaction(SIGUSR1, SIG_IGN);
  kill(mypid, SIGUSR1);
  {
    List<int>* q = signal_safe->TakePendingSignals();
    ASSERT(q != nullptr);
    ASSERT(len(q) == 0);
    signal_safe->ReuseEmptyList(q);
  }
  iolib::sigaction(SIGUSR2, SIG_IGN);

  iolib::RegisterSignalInterest(SIGWINCH);

  kill(mypid, SIGWINCH);
  ASSERT_EQ(iolib::UNTRAPPED_SIGWINCH, signal_safe->LastSignal());

  signal_safe->SetSigWinchCode(SIGWINCH);

  kill(mypid, SIGWINCH);
  ASSERT_EQ(SIGWINCH, signal_safe->LastSignal());
  {
    List<int>* q = signal_safe->TakePendingSignals();
    ASSERT(q != nullptr);
    ASSERT_EQ(2, len(q));
    ASSERT_EQ(SIGWINCH, q->at(0));
    ASSERT_EQ(SIGWINCH, q->at(1));
  }

  PASS();
}

TEST signal_safe_test() {
  iolib::SignalSafe signal_safe;

  List<int>* received = signal_safe.TakePendingSignals();

  // We got now signals
  ASSERT_EQ_FMT(0, len(received), "%d");

  // The existing queue is of length 0
  ASSERT_EQ_FMT(0, len(signal_safe.pending_signals_), "%d");

  // Capacity is a ROUND NUMBER from the allocator's POV
  // There's no convenient way to test the obj_len we pass to gHeap.Allocate,
  // but it should be (1022 + 2) * 4.
  ASSERT_EQ_FMT(1022, signal_safe.pending_signals_->capacity_, "%d");

  // Register too many signals
  for (int i = 0; i < iolib::kMaxPendingSignals + 10; ++i) {
    signal_safe.UpdateFromSignalHandler(SIGINT);
  }

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(signal_test);
  RUN_TEST(signal_safe_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */

  return 0;
}
