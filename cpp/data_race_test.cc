// cpp/data_race_test.cc
//
// The idea behind this test is that these two questions have the SAME answer:
//
// 1. It it safe to perform operations X and Y on 2 different threads without
//    synchronization?  (If they share nontrivial state, then no.)
// 2. It it safe to perform operations X in a signal handler and operation Y in
//    the main thread without synchronization

#include <pthread.h>

#include <map>

#include "cpp/leaky_core.h"
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

void* ListThread(void* p) {
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
  pthread_create(&t, 0, ListThread, mylist);
  // DATA RACE DETECTED by ThreadSanitizer!  Remove this line, and it goes
  // away.
  mylist->append(StrFromC("concurrent"));
  pthread_join(t, 0);

  PASS();
}

TEST global_trap_state_test() {
  log("global_trap_state_test");

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(tsan_demo);
  RUN_TEST(list_test);
  RUN_TEST(global_trap_state_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
