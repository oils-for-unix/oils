// cpp/data_race_test.cc
//
// The idea behind this test is that these two questions have the SAME answer:
//
// 1. Is it safe to perform ops X and Y in 2 different threads, without
//    synchronization?  (If they share nontrivial state, then NO.)
// 2. Is it safe to perform op X in a signal handler, and op Y in the main
//    thread, without synchronization?

#include <pthread.h>

#include <atomic>
#include <map>

#include "cpp/core.h"
#include "mycpp/runtime.h"
#include "vendor/greatest.h"

// Example from
// https://github.com/google/sanitizers/wiki/ThreadSanitizerCppManual

typedef std::map<std::string, std::string> map_t;

void* MapThread(void* p) {
  map_t& m = *(static_cast<map_t*>(p));
  m["foo"] = "bar";
  return nullptr;
}

TEST tsan_demo() {
  map_t m;
  pthread_t t;
#if 1
  pthread_create(&t, 0, MapThread, &m);
  printf("foo=%s\n", m["foo"].c_str());
  pthread_join(t, 0);
#endif

  PASS();
}

void* AppendListThread(void* p) {
  List<BigStr*>* mylist = static_cast<List<BigStr*>*>(p);
  mylist->append(StrFromC("thread"));
  return nullptr;
}

TEST list_test() {
  List<BigStr*>* mylist = nullptr;
  StackRoots _roots({&mylist});

  mylist = NewList<BigStr*>({});
  mylist->append(StrFromC("main"));

  pthread_t t;
  pthread_create(&t, 0, AppendListThread, mylist);
  // DATA RACE DETECTED by ThreadSanitizer!  You can't append to a List from
  // two threads concurrently.
#if 1
  mylist->append(StrFromC("concurrent"));
#endif
  pthread_join(t, 0);

  PASS();
}

void* SimulateSignalHandlers(void* p) {
  auto signal_safe = static_cast<pyos::SignalSafe*>(p);

  // Send a whole bunch of SIGINT in a tight loop, which will append to
  // List<int> signal_queue_.
  for (int i = 0; i < pyos::kMaxPendingSignals + 10; ++i) {
    // This line can race with PollSigInt and LastSignal
    signal_safe->UpdateFromSignalHandler(SIGINT);

    // This line can race with SetSigWinchCode
    signal_safe->UpdateFromSignalHandler(SIGWINCH);
  }
  return nullptr;
}

TEST take_pending_signals_test() {
  pyos::SignalSafe signal_safe;

  // Background thread that simulates signal handler
  pthread_t t;
  pthread_create(&t, 0, SimulateSignalHandlers, &signal_safe);

  // Concurrent access in main thread
  List<int>* received = signal_safe.TakePendingSignals();
  log("(1) received %d signals", len(received));

  received->clear();
  signal_safe.ReuseEmptyList(received);

  received = signal_safe.TakePendingSignals();
  log("(2) received %d signals", len(received));

  pthread_join(t, 0);

  PASS();
}

TEST set_sigwinch_test() {
  pyos::SignalSafe signal_safe;

  // Background thread that simulates signal handler
  pthread_t t;
  pthread_create(&t, 0, SimulateSignalHandlers, &signal_safe);

  // Concurrent access in main thread
  signal_safe.SetSigWinchCode(pyos::UNTRAPPED_SIGWINCH);

  pthread_join(t, 0);
  PASS();
}

// #define LOCK_FREE_ATOMICS in core.h makes this PASS ThreadSanitizer

TEST last_signal_test() {
  pyos::SignalSafe signal_safe;

  // Background thread that simulates signal handler
  pthread_t t;
  pthread_create(&t, 0, SimulateSignalHandlers, &signal_safe);

  // Concurrent access in main thread
  int last_signal = signal_safe.LastSignal();
  log("last signal = %d", last_signal);

  pthread_join(t, 0);
  PASS();
}

TEST poll_sigint_test() {
  pyos::SignalSafe signal_safe;

  // Background thread that simulates signal handler
  pthread_t t;
  pthread_create(&t, 0, SimulateSignalHandlers, &signal_safe);

  // Concurrent access in main thread
  bool sigint = signal_safe.PollSigInt();
  log("sigint? = %d", sigint);

  pthread_join(t, 0);
  PASS();
}

TEST poll_sigwinch_test() {
  pyos::SignalSafe signal_safe;

  // Background thread that simulates signal handler
  pthread_t t;
  pthread_create(&t, 0, SimulateSignalHandlers, &signal_safe);

  // Concurrent access in main thread
  bool sigwinch = signal_safe.PollSigWinch();
  log("sigwinch? = %d", sigwinch);

  pthread_join(t, 0);
  PASS();
}

TEST atomic_demo() {
  std::atomic<int> a(3);

  // true on my machine
  log("is_lock_free = %d", a.is_lock_free());

  log("a.load() = %d", a.load());

  a.store(42);

  log("a.load() = %d", a.load());

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(tsan_demo);
  RUN_TEST(list_test);

  // SignalSafe tests
  RUN_TEST(take_pending_signals_test);
  RUN_TEST(set_sigwinch_test);
  RUN_TEST(last_signal_test);
  RUN_TEST(poll_sigint_test);
  RUN_TEST(poll_sigwinch_test);

  RUN_TEST(atomic_demo);

  // Also test: Can MarkObjects() race with UpdateFromSignalHandler() ?  It
  // only reads the ObjHeader, so it doesn't seem like it.

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
