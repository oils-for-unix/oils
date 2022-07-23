// gc_stress_test.cc: Do many allocations and collections under ASAN
//
// And with GC_STATS defined.

#include "mycpp/gc_builtins.h"
#include "mycpp/gc_types.h"
#include "vendor/greatest.h"
//#include "gc_mylib.h"  // gBuf

using gc_heap::Alloc;
using gc_heap::Dict;
using gc_heap::List;
using gc_heap::NewList;
using gc_heap::StackRoots;
using gc_heap::Str;
using gc_heap::StrFromC;
// using gc_heap::kEmptyString;

using gc_heap::gHeap;

// TODO:
// - Assert the number of collections
// - Assert the number of heap growths
// - maybe number of allocations?

TEST str_simple_test() {
  gHeap.Init(1 << 8);  // 1 KiB

  Str* s = nullptr;
  // Note: This test case doesn't strictly require this.  I guess because
  // it doesn't use the strings long after they've been allocated and/or moved.
  StackRoots _roots({&s});

  int total = 0;
  for (int i = 0; i < 400; ++i) {
    unsigned char c = i % 256;
    s = chr(c);
    // print(s);
    log("i = %d", i);
    ASSERT_EQ_FMT(c, ord(s), "%d");  // Check for memory corruption
    total += len(s);
  }
  log("total = %d", total);
#ifdef GC_STATS
  gHeap.Report();
#endif

  PASS();
}

GLOBAL_STR(b, "b");
GLOBAL_STR(bx, "bx");

TEST str_growth_test() {
  gHeap.Init(1 << 8);  // 1 KiB

  Str* s = nullptr;
  StackRoots _roots({&s});

#ifdef GC_STATS
  gHeap.Report();
#endif

  s = StrFromC("b");
  int n = 300;
  int total = 0;
  for (int i = 0; i < n; ++i) {
    total += len(s);  // count it first

    // log("--- %p %d", s, len(s));
    // print(s);
    s = s->replace(b, bx);
    // print(s);
  }
  log("total = %d", total);

  int expected = (n * (n + 1)) / 2;
  ASSERT_EQ_FMT(expected, total, "%d");

#ifdef GC_STATS
  gHeap.Report();
#endif

  PASS();
}

// Simple test with just List on the heap.
TEST list_append_test() {
  gHeap.Init(1 << 8);  // 1 KiB

  List<int>* L = nullptr;
  StackRoots _roots({&L});

  int length = 1;
  L = NewList<int>(42, length);

  int n = 1000;
  int total = 0;
  for (int i = 0; i < n; ++i) {
    total += len(L);  // count it first

    // log("sliced L = %p", L);
    L->append(43);  // append to end
  }
  log("total = %d", total);
  ASSERT_EQ_FMT(500500, total, "%d");

  PASS();
}

TEST list_slice_append_test() {
  gHeap.Init(1 << 8);  // 1 KiB

  List<int>* L = nullptr;
  StackRoots _roots({&L});

  int length = 5;
  L = NewList<int>(42, length);

  int n = 300;
  int total = 0;
  for (int i = 0; i < n; ++i) {
    log("i = %d", i);
    total += len(L);  // count it first

    L = L->slice(1);
    L->append(43);  // append to end
  }
  log("total = %d", total);

  int expected = n * length;
  ASSERT_EQ_FMT(expected, total, "%d");

  PASS();
}

TEST list_str_growth_test() {
  gHeap.Init(1 << 8);  // 1 KiB

  Str* s = nullptr;
  List<Str*>* L = nullptr;
  StackRoots _roots({&s, &L});
  // StackRoots _roots({&L});

  s = StrFromC("b");
  L = Alloc<List<Str*>>();

#if 0
  int total = 0;
  int n = 40;
  for (int i = 0; i < n; ++i) {
    log("i = %d", i);
    //total += len(s);

    L->append(s);

    // This works if we don't have 's'.  Because it's global?
    //L->append(bx);
  }
  log("total = %d", total);

  int expected = (n * (n + 1)) / 2;
  ASSERT_EQ_FMT(expected, total, "%d");
#endif

  PASS();
}

TEST dict_growth_test() {
  gHeap.Init(1 << 8);  // 1 KiB

  Str* s = nullptr;
  Dict<Str*, int>* D = nullptr;
  StackRoots _roots({&s, &D});

  s = StrFromC("abcdefg");
  D = Alloc<Dict<Str*, int>>();

  int total = 0;
  for (int i = 0; i < 40; ++i) {
    total += len(s);
    s = s->replace(b, bx);
    D->set(s, 42);
  }
  log("total = %d", total);

  // TODO: Test NewDict(), etc.

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(str_simple_test);
  RUN_TEST(str_growth_test);
  RUN_TEST(list_append_test);
  RUN_TEST(list_slice_append_test);
  RUN_TEST(list_str_growth_test);
  RUN_TEST(dict_growth_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
