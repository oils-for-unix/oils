#include "mycpp/mark_sweep_heap.h"

#include "mycpp/gc_alloc.h"  // gHeap
#include "mycpp/gc_list.h"
#include "vendor/greatest.h"

TEST for_code_coverage() {
  // Add coverage for some methods

  gHeap.ProcessExit();

  PASS();
}

TEST mark_set_test() {
  MarkSet mark_set;
  mark_set.ReInit(20);

  for (int i = 0; i < 20; ++i) {
    ASSERT_EQ(false, mark_set.IsMarked(i));
  }

  for (int i = 0; i < 10; ++i) {
    mark_set.Mark(i);
    ASSERT_EQ(true, mark_set.IsMarked(i));
  }

  for (int i = 10; i < 20; ++i) {
    ASSERT_EQ(false, mark_set.IsMarked(i));
  }

  mark_set.Debug();

  // Another collection
  int big = 1000;
  mark_set.ReInit(big);

  for (int i = 0; i < 20; ++i) {
    ASSERT_EQ(false, mark_set.IsMarked(i));
  }
  for (int i = big - 100; i < big; ++i) {
    ASSERT_EQ(false, mark_set.IsMarked(i));
  }

  ASSERT_EQ(false, mark_set.IsMarked(big));
  mark_set.Mark(big);
  ASSERT_EQ(true, mark_set.IsMarked(big));

  // ASAN will detect buffer overflow
  // mark_set.Mark(13220);

  PASS();
}

TEST api_test() {
#ifdef GC_ALWAYS
  // no objects live
  ASSERT_EQ_FMT(0, gHeap.MaybeCollect(), "%d");
  {
    Str *s1 = StrFromC("foo");
    Str *s2 = StrFromC("bar");
    StackRoots _r({&s1, &s2});

    // 2 live objects
    ASSERT_EQ_FMT(2, gHeap.MaybeCollect(), "%d");

    // 1 live
    s2 = nullptr;
    ASSERT_EQ_FMT(1, gHeap.MaybeCollect(), "%d");
  }
  ASSERT_EQ_FMT(0, gHeap.MaybeCollect(), "%d");
#else
  // otherwise we didn't try to collect
  ASSERT_EQ_FMT(-1, gHeap.MaybeCollect(), "%d");
#endif

  PASS();
}

TEST string_collection_test() {
  Str *test_str = StrFromC("foo");

  StackRoots _roots({&test_str});

  ASSERT(are_equal(test_str, StrFromC("foo")));

  gHeap.Collect();

  ASSERT(are_equal(test_str, StrFromC("foo")));

  PASS();
}

TEST list_collection_test() {
  {
    Str *test_str0 = nullptr;
    Str *test_str1 = nullptr;
    List<Str *> *test_list = nullptr;

    StackRoots _roots({&test_str0, &test_str1, &test_list});

    test_str0 = StrFromC("foo_0");
    test_str1 = StrFromC("foo_1");
    test_list = NewList<Str *>();

    test_list->append(test_str0);
    test_list->append(test_str1);

    // Verify the list looks as we expected
    {
      ASSERT(are_equal(test_list->at(0), test_str0));
      ASSERT(are_equal(test_list->at(1), test_str1));

      ASSERT_EQ(test_list->at(0), test_str0);
      ASSERT_EQ(test_list->at(1), test_str1);

      ASSERT_EQ(2, len(test_list));
    }

    gHeap.Collect();

    {
      ASSERT(are_equal(test_list->at(0), test_str0));
      ASSERT(are_equal(test_list->at(1), test_str1));

      ASSERT_EQ(test_list->at(0), test_str0);
      ASSERT_EQ(test_list->at(1), test_str1);
    }

    test_list->pop();
    ASSERT_EQ(1, len(test_list));
  }

  gHeap.Collect();

  PASS();
}

class Node {
 public:
  Node() : next_(nullptr) {
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(Node));
  }

  Node *next_;

  static constexpr uint32_t field_mask() {
    return maskbit(offsetof(Node, next_));
  }
};

TEST cycle_collection_test() {
  // Dict<Str*, int>* d = NewDict<Str*, int>();

  Node *n1 = nullptr;
  Node *n2 = nullptr;
  StackRoots _roots({&n1, &n2});
  n1 = Alloc<Node>();
  n2 = Alloc<Node>();

  gHeap.Collect();

  n1->next_ = n2;
  n2->next_ = n1;

  gHeap.Collect();

  PASS();
}

TEST pool_sanity_check() {
  Pool<2, 32> p;

  ASSERT_EQ(p.bytes_allocated(), 0);
  ASSERT_EQ(p.num_allocated(), 0);
  ASSERT_EQ(p.num_live(), 0);
  ASSERT_EQ(p.kMaxObjSize, 32);

  int obj_id1 = -1;
  int obj_id2 = -1;
  int obj_id3 = -1;
  p.Allocate(&obj_id1);
  p.Allocate(&obj_id2);
  p.Allocate(&obj_id3);
  ASSERT_EQ(p.num_allocated(), 3);
  ASSERT_EQ(p.num_live(), 3);
  // The third allocation should've created a new block.
  ASSERT_EQ(p.bytes_allocated(), 128);
  ASSERT(obj_id1 != -1);
  ASSERT(obj_id2 != -1);
  ASSERT(obj_id3 != -1);

  p.Free();
  PASS();
}

TEST pool_sweep() {
  Pool<2, 32> p;

  p.PrepareForGc();
  p.Sweep();

  int obj_id;
  void *addr1 = p.Allocate(&obj_id);
  void *addr2 = p.Allocate(&obj_id);
  p.PrepareForGc();
  p.Sweep();

  ASSERT_EQ(p.num_live(), 0);

  // Cells are reused after freeing.
  void *addr3 = p.Allocate(&obj_id);
  void *addr4 = p.Allocate(&obj_id);
  ASSERT((addr1 == addr3 && addr2 == addr4) ||
         (addr1 == addr4 && addr2 == addr3));

  p.Free();
  PASS();
}

TEST pool_marked_objs_are_kept_alive() {
  Pool<1, 32> p;

  int obj_id1;
  int obj_id2;
  p.Allocate(&obj_id1);
  p.Allocate(&obj_id2);
  p.PrepareForGc();
  p.Mark(obj_id2);
  p.Sweep();
  ASSERT_EQ(p.num_live(), 1);

  p.Free();
  PASS();
}

TEST pool_size() {
  MarkSweepHeap heap;
  log("pool1 kMaxObjSize %d", heap.pool1_.kMaxObjSize);
  log("pool1 kBlockSize %d", heap.pool1_.kBlockSize);

  log("pool2 kMaxObjSize %d", heap.pool2_.kMaxObjSize);
  log("pool2 kBlockSize %d", heap.pool2_.kBlockSize);

  // It may do malloc(sizeof(Block)) each time, e.g. 4080 bytes
  for (int i = 0; i < 200; ++i) {
    int obj_id = 0;
    heap.pool1_.Allocate(&obj_id);
    // log("pool1 obj_id = %d", obj_id);
  }

  for (int i = 0; i < 200; ++i) {
    int obj_id = 0;
    heap.pool2_.Allocate(&obj_id);
    // log("pool2 obj_id = %d", obj_id);
  }

  heap.pool1_.Free();
  heap.pool2_.Free();

  PASS();
}

SUITE(pool_alloc) {
  RUN_TEST(pool_sanity_check);
  RUN_TEST(pool_sweep);
  RUN_TEST(pool_marked_objs_are_kept_alive);
  RUN_TEST(pool_size);
}

int f(Str *s, List<int> *mylist) {
  // Param Roots
  StackRoots _roots({&s, &mylist});

  // Sorted params
  Str *first = nullptr;
  List<int> *other = nullptr;
  List<int> *other2 = nullptr;
  Str *last = nullptr;

  int a = 0;
  float b = 3.5;

  ptrdiff_t diff = &last - &first;

  // Account for stack going up or down
  // This is cool!
  int n_pointers = diff > 0 ? diff : -diff;

  log("a = %d, b = %f", a, b);

  // 2 pointers if we don't use other2 !
  // log("other = %p", &other);

  // 3 pointers!
  log("other = %p, other2 = %p", &other, &other2);

  log("n_pointers = %d", n_pointers);

  return 42;
}

TEST hybrid_root_test() {
  log("hi = %s", "x");

  f(StrFromC("hi"), nullptr);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char **argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(for_code_coverage);
  RUN_TEST(mark_set_test);
  RUN_TEST(api_test);
  RUN_TEST(string_collection_test);
  RUN_TEST(list_collection_test);
  RUN_TEST(cycle_collection_test);

  RUN_SUITE(pool_alloc);

  RUN_TEST(hybrid_root_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
