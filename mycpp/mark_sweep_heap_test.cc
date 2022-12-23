#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST for_code_coverage() {
  // Add coverage for some methods

  void *p = gHeap.Allocate(10);
  void *q = gHeap.Reallocate(p, 20);

  ASSERT(p != nullptr);
  ASSERT(q != nullptr);

  gHeap.FastProcessExit();

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

  {
    // NOTE(Jesse): This causes a crash when this gets compiled against the
    // cheney collector w/ GC_ALWAYS.  I did verify it doesn't crash with
    // the marksweep allocator but didn't want to figure out how to tell the
    // build system to not compile these tests against the cheney collector
    //
    /* ASSERT(are_equal(test_str, StrFromC("foo"))); */

    StackRoots _roots({&test_str});

    ASSERT(are_equal(test_str, StrFromC("foo")));

    gHeap.Collect();

    ASSERT(are_equal(test_str, StrFromC("foo")));
  }

  // NOTE(Jesse): Technically UB.  If the collector hits between when the roots
  // go out of scope in the above block we'll get a UAF here.  ASAN should
  // detect this but we currently have no way of programatically verifying that
  // ASAN detects bugs.  AFAIK asan is not 100% reliable, so maybe that's a
  // path fraught with peril anyhow.
  //
  /* ASSERT(are_equal(test_str, StrFromC("foo"))); */

  gHeap.Collect();

  // NOTE(Jesse): ASAN detects UAF here when I tested by toggling this on
  //
  // ASSERT(are_equal(test_str, StrFromC("foo")));

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
      ASSERT(are_equal(test_list->index_(0), test_str0));
      ASSERT(are_equal(test_list->index_(1), test_str1));

      ASSERT_EQ(test_list->index_(0), test_str0);
      ASSERT_EQ(test_list->index_(1), test_str1);

      ASSERT_EQ(2, len(test_list));
    }

    gHeap.Collect();

    {
      ASSERT(are_equal(test_list->index_(0), test_str0));
      ASSERT(are_equal(test_list->index_(1), test_str1));

      ASSERT_EQ(test_list->index_(0), test_str0);
      ASSERT_EQ(test_list->index_(1), test_str1);
    }

    test_list->pop();
    ASSERT_EQ(1, len(test_list));
  }

  gHeap.Collect();

  PASS();
}

class Node : Obj {
 public:
  Node();
  Node *next_;
};

constexpr uint16_t maskof_Node() {
  return maskbit(offsetof(Node, next_));
}

Node::Node()
    : Obj(Tag::FixedSize, maskof_Node(), sizeof(Node)), next_(nullptr) {
}

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

GREATEST_MAIN_DEFS();

int main(int argc, char **argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(for_code_coverage);
  RUN_TEST(api_test);
  RUN_TEST(string_collection_test);
  RUN_TEST(list_collection_test);
  RUN_TEST(cycle_collection_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
