// cpp/data_race_test.cc
//
// The idea behind this test is that these two questions have the SAME answer:
//
// 1. Is it safe to perform ops X and Y in 2 different threads, without
//    synchronization?  (If they share nontrivial state, then NO.)
// 2. Is it safe to perform op X in a signal handler, and op Y in the main
//    thread, without synchronization?

#include <pthread.h>

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
  List<Str*>* mylist = static_cast<List<Str*>*>(p);
  mylist->append(StrFromC("thread"));
  return nullptr;
}

TEST list_test() {
  List<Str*>* mylist = nullptr;
  StackRoots _roots({&mylist});

  mylist = NewList<Str*>({});
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
  for (int i = 0; i < pyos::kMaxSignalsInFlight + 10; ++i) {

    // This line can race with PollSigInt and LastSignal
    signal_safe->UpdateFromSignalHandler(SIGINT);

    // This line can race with SetSigWinchCode
    signal_safe->UpdateFromSignalHandler(SIGWINCH);
  }
  return nullptr;
}

TEST signal_safe_test() {
  pyos::SignalSafe signal_safe;

  // Create background thread that simulates signal handler
  pthread_t t;
  pthread_create(&t, 0, SimulateSignalHandlers, &signal_safe);

  // Test FOUR different functions we call from the main thread

#if 0
  List<int>* received;
  received = signal_safe.TakeSignalQueue();
  log("received 1 %d", len(received));
#endif

#if 0
  signal_safe.SetSigWinchCode(pyos::UNTRAPPED_SIGWINCH);
#endif

#if 0
  int last_signal = signal_safe.LastSignal();
  log("last signal = %d", last_signal);
#endif

#if 1
  bool sigint = signal_safe.PollSigInt();
  log("sigint? = %d", sigint);
#endif

  pthread_join(t, 0);

  // Also test: Can MarkObjects() race with UpdateFromSignalHandler() ?  It
  // only reads the ObjHeader, so it doesn't seem like it.

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(tsan_demo);
  RUN_TEST(list_test);
  RUN_TEST(signal_safe_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
