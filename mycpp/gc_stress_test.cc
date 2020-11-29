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

GLOBAL_STR(b, "b");
GLOBAL_STR(bb, "bx");

// TODO:
// - Assert the number of collections
// - Assert the number of heap growths
// - maybe number of allocations?

TEST str_collect_test() {
  gHeap.Init(1 << 8);  // 1 KiB

  Str* s;
  Str* t;
  // Why isn't this necessary?  I thought it woudl realloc.
  StackRoots({&s});
  
  s = NewStr("abcdefg");

#if 0
  int total = 0;
  for (int i = 0; i < 4000; ++i) {
    s = s->replace(b, bb);
    print(s);
    total += len(s);
    log("%d", len(s));

    // hit NUL termination path
    //t = NewStr("NUL");
    //total += len(t);

    // log("i = %d", i);
    // log("len(s) = %d", len(s));
  }
  log("total = %d", total);
#endif

  gHeap.Report();

  PASS();
}

TEST list_collect_test() {
  gHeap.Init(1 << 8);  // 1 KiB

  Str* s;
  List<Str*>* L;
  StackRoots({&s, &L});

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

TEST dict_collect_test() {
  gHeap.Init(1 << 8);  // 1 KiB

  Str* s;
  Dict<Str*, int>* D;
  StackRoots({&s, &D});

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

  RUN_TEST(str_collect_test);
  RUN_TEST(list_collect_test);
  RUN_TEST(dict_collect_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
