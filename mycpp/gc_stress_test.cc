// gc_stress_test.cc: Do many allocations and collections under ASAN
//
// And with GC_DEBUG defined.

#include "gc_heap.h"
#include "greatest.h"
#include "my_runtime.h"
//#include "mylib2.h"  // gBuf

using gc_heap::Alloc;
using gc_heap::Dict;
using gc_heap::List;
using gc_heap::NewStr;
using gc_heap::StackRoots;
using gc_heap::Str;
// using gc_heap::kEmptyString;

using gc_heap::gHeap;

// TODO:
// - Assert the number of collections
// - Assert the number of heap growths
// - maybe number of allocations?

TEST str_simple_test() {
  gHeap.Init(1 << 8);  // 1 KiB

  Str* s;
  // Note: This test case doesn't strictly require this.  I guess because
  // it doesn't use the strings long after they've been allocated and/or moved.
  StackRoots _roots({&s});

  int total = 0;
  for (int i = 0; i < 400; ++i) {
    unsigned char c = i % 256;
    s = chr(c);
    // print(s);
    ASSERT_EQ_FMT(c, ord(s), "%d");  // Check for memory corruption
    total += len(s);
  }
  log("total = %d", total);
  gHeap.Report();

  PASS();
}

GLOBAL_STR(b, "b");
GLOBAL_STR(bb, "bx");

TEST str_growth_test() {
  gHeap.Init(1 << 8);  // 1 KiB

  Str* s;
  StackRoots _roots({&s});

  gHeap.Report();

  s = NewStr("b");
#if 1
  int n = 300;
  int total = 0;
  for (int i = 0; i < n; ++i) {
    total += len(s);  // count it first

    // log("--- %p %d", s, len(s));
    // print(s);
    s = s->replace(b, bb);
    // print(s);

    // hit NUL termination path
    // t = NewStr("NUL");
    // total += len(t);

    // log("i = %d", i);
    // log("len(s) = %d", len(s));
  }
  log("total = %d", total);

  int expected = (n * (n + 1)) / 2;
  ASSERT_EQ_FMT(expected, total, "%d");
#endif

  gHeap.Report();

  PASS();
}

TEST list_growth_test() {
  gHeap.Init(1 << 8);  // 1 KiB

  Str* s;
  List<Str*>* L;
  StackRoots _roots({&s, &L});

  s = NewStr("abcdefg");
  L = Alloc<List<Str*>>();

#if 0
  int total = 0;
  for (int i = 0; i < 40; ++i) {
    //s = s->replace(b, bb);
    L->append(s);
    total += len(s);
  }
  log("total = %d", total);
#endif

  PASS();
}

TEST dict_growth_test() {
  gHeap.Init(1 << 8);  // 1 KiB

  Str* s;
  Dict<Str*, int>* D;
  StackRoots _roots({&s, &D});

  s = NewStr("abcdefg");
  D = Alloc<Dict<Str*, int>>();

#if 0
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

  RUN_TEST(str_simple_test);
  RUN_TEST(str_growth_test);
  RUN_TEST(list_growth_test);
  RUN_TEST(dict_growth_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
