// gc_stress_test.cc: Do many allocations and collections under ASAN
//
// And with GC_DEBUG defined.

#include "gc_heap.h"
#include "greatest.h"
//#include "my_runtime.h"
//#include "mylib2.h"  // gBuf

using gc_heap::Alloc;
using gc_heap::Dict;
using gc_heap::List;
using gc_heap::NewStr;
using gc_heap::Str;
// using gc_heap::kEmptyString;

using gc_heap::gHeap;

GLOBAL_STR(b, "b");
GLOBAL_STR(bb, "bx");

// TODO:
// - Assert the number of collections
// - Assert the number of heap growths
// - maybe number of allocations?

TEST str_collect_test() {
  gHeap.Init(1 << 8);  // 1 KiB

  auto s = NewStr("abcdefg");
  int total = 0;
  for (int i = 0; i < 40; ++i) {
    s = s->replace(b, bb);
    total += len(s);

    // hit NUL termination path
    s = NewStr("NUL");
    total += len(s);

    // log("i = %d", i);
    // log("len(s) = %d", len(s));
  }
  log("total = %d", total);

  PASS();
}

TEST list_collect_test() {
  gHeap.Init(1 << 8);  // 1 KiB

#if 0
  auto s = NewStr("abcdefg");
  auto L = Alloc<List<Str*>>();

  int total = 0;
  for (int i = 0; i < 40; ++i) {
    s = s->replace(b, bb);
    L->append(s);
    total += len(s);
  }
  log("total = %d", total);
#endif

  PASS();
}

TEST dict_collect_test() {
  gHeap.Init(1 << 8);  // 1 KiB
#if 0
  auto s = NewStr("abcdefg");
  auto D = Alloc<Dict<Str*, int>>();

  int total = 0;
  for (int i = 0; i < 40; ++i) {
    s = s->replace(b, bb);
    D->set(s, 42);
    total += len(s);
  }
  log("total = %d", total);
#endif

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(str_collect_test);
  RUN_TEST(list_collect_test);
  RUN_TEST(dict_collect_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
