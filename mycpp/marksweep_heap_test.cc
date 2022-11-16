#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST string_collection_test() {
  Str *test_str = StrFromC("foo");

  {
    // NOTE(Jesse): This causes a crash when this gets compiled against the
    // cheney collector w/ GC_EVERY_ALLOC.  I did verify it doesn't crash with
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

TEST root_set_test() {
  RootSet r(32);

  // Make sure it was initialized correctly

  // 32 pre-allocated frames
  ASSERT_EQ_FMT(32, static_cast<int>(r.stack_.capacity()), "%d");
  ASSERT_EQ_FMT(32, static_cast<int>(r.stack_.size()), "%d");

  // reserved 16 rooted objects per frame
  for (int i = 0; i < 32; ++i) {
    ASSERT_EQ_FMT(16, static_cast<int>(r.stack_[i].capacity()), "%d");
    ASSERT_EQ_FMT(0, static_cast<int>(r.stack_[i].size()), "%d");
  }

  /*
  Str* g() {
    Str* ret = StrFromC("X");
    gHeap.RootOnReturn(ret);
    return ret;
  }

  Str* f(Str* s, Str* t) {
    Str* ret = str_concat(s, t);
    gHeap.RootOnReturn(ret);
    return ret;
  }

  int main() {
    Str* dummy = f(g(), g());

    // both the temporary args and concatenated values are roots until the end
  of main()
  }
  */

  ASSERT_EQ_FMT(0, r.NumRoots(), "%d");
  ASSERT_EQ_FMT(1, r.NumFrames(), "%d");

  r.PushFrame();  // main() call
  ASSERT_EQ_FMT(0, r.NumRoots(), "%d");
  ASSERT_EQ_FMT(2, r.NumFrames(), "%d");

  r.PushFrame();  // g() call
  ASSERT_EQ_FMT(0, r.NumRoots(), "%d");
  ASSERT_EQ_FMT(3, r.NumFrames(), "%d");

  // g() returns "X"
  r.RootOnReturn(StrFromC("X"));
  ASSERT_EQ_FMT(1, r.NumRoots(), "%d");
  ASSERT_EQ_FMT(3, r.NumFrames(), "%d");
  ASSERT_EQ_FMT(1, static_cast<int>(r.stack_[1].size()), "%d");
  ASSERT_EQ_FMT(0, static_cast<int>(r.stack_[2].size()), "%d");

  r.PopFrame();  // g() return
  // "X" is still live after foo() returns!
  ASSERT_EQ_FMT(1, r.NumRoots(), "%d");
  ASSERT_EQ_FMT(2, r.NumFrames(), "%d");
  ASSERT_EQ_FMT(1, static_cast<int>(r.stack_[1].size()), "%d");

  r.PushFrame();  // another g() call
  ASSERT_EQ_FMT(1, r.NumRoots(), "%d");
  ASSERT_EQ_FMT(3, r.NumFrames(), "%d");

  // g() returns "X" again
  r.RootOnReturn(StrFromC("X"));
  ASSERT_EQ_FMT(2, r.NumRoots(), "%d");
  ASSERT_EQ_FMT(3, r.NumFrames(), "%d");
  ASSERT_EQ_FMT(2, static_cast<int>(r.stack_[1].size()), "%d");
  ASSERT_EQ_FMT(0, static_cast<int>(r.stack_[2].size()), "%d");

  r.PopFrame();  // another g() return
  ASSERT_EQ_FMT(2, r.NumRoots(), "%d");
  ASSERT_EQ_FMT(2, r.NumFrames(), "%d");
  ASSERT_EQ_FMT(2, static_cast<int>(r.stack_[1].size()), "%d");

  r.PopFrame();  // main() return
  ASSERT_EQ_FMT(1, r.NumFrames(), "%d");
  ASSERT_EQ_FMT(0, r.NumRoots(), "%d");

  PASS();
}

TEST root_set_null_test() {
  RootSet r(32);

  r.PushFrame();
  r.PushFrame();

  r.RootOnReturn(StrFromC("X"));
  ASSERT_EQ_FMT(1, r.NumRoots(), "%d");

  // Does NOT get added
  r.RootOnReturn(nullptr);
  ASSERT_EQ_FMT(1, r.NumRoots(), "%d");

  r.PopFrame();
  r.PopFrame();

  PASS();
}

TEST root_set_big_test() {
  Str *s = StrFromC("Y");

  RootSet r(32);
  // Test many frames
  r.PushFrame();
  for (int i = 0; i < 100; ++i) {
    // log("i %d", i);
    r.PushFrame();
    for (int j = 0; j < 100; ++j) {
      r.RootOnReturn(s);
    }
  }

  PASS();
}

int f() {
  RootsFrame r2;

  // Can't assert in this non-test function
  return gHeap.root_set_.NumFrames();
}

Str *g(Str *left, Str *right) {
  RootsFrame _r;

  // TODO: call str_concat, NewList, etc.
  Str *ret = left;
  gHeap.RootOnReturn(ret);
  return ret;
}

int count_old(Str *a, Str *b) {
  StackRoots _roots({&a, &b});

  int result = 0;
  if (a) {
    result += len(a);
  }
  if (b) {
    result += len(b);
  }
  return result;
}

// Like the above, but instead of rooting variables, we create a RootsFrame
// instance.  It doesn't return a heap-allocated object, so we don't need
// gHeap.RootOnReturn(). Functions that allocate like Alloc<T> are responsible
// for that.

int count_new(Str *a, Str *b) {
  RootsFrame _r;

  int result = 0;
  if (a) {
    result += len(a);
  }
  if (b) {
    result += len(b);
  }
  return result;
}

TEST old_slice_demo() {
  Str *s = nullptr;
  Str *t = nullptr;
  StackRoots _roots({&s, &t});
  s = StrFromC("spam");
  t = StrFromC("eggs");

  log("old_slice_demo");

  // OK
  int i = count_old(s->slice(1), nullptr);
  log("s[1:] %d", i);

  // OK
  int j = count_old(t->slice(2), nullptr);
  log("t[2:] %d", j);

  // f(g(), h()) problem -- ASAN in gcevery mode finds this!
  int k = count_old(s->slice(1), t->slice(2));
  log("s[1:] t[2:] %d", k);

  PASS();
}

TEST new_slice_demo() {
  RootsFrame _r;

  Str *s = StrFromC("spam");
  log("s %p heap_tag_ %d", s, s->heap_tag_);
  log("");
  Str *t = StrFromC("eggs");
  log("t %p heap_tag_ %d", t, t->heap_tag_);
  log("");

  log("new_slice_demo");

  // OK
  int i = count_new(s->slice(1), nullptr);
  log("s[1:] %d", i);

  // OK
  int j = count_new(t->slice(2), nullptr);
  log("t[2:] %d", j);

  // Does NOT have the f(g(), h()) problem
  int k = count_new(s->slice(1), t->slice(2));
  log("s[1:] t[2:] %d", k);

  PASS();
}

TEST root_set_stress_test() {
  RootsFrame _r;

  for (int i = 0; i < 10; ++i) {
    // NewStr needs to root; also needs RootsFrame
    Str *s = StrFromC("abcdef");

    // slice() needs to root; also eneds RootsFrame
    Str *t = g(s->slice(1), s->slice(2));

    log("t = %s", t->data());
  }

  PASS();
}

static List<int> *gList = nullptr;
TEST rooting_scope_test() {
  ASSERT_EQ_FMT(1, gHeap.root_set_.NumFrames(), "%d");

  RootsFrame r1;
  ASSERT_EQ_FMT(2, gHeap.root_set_.NumFrames(), "%d");

  int f_num_frames = f();
  ASSERT_EQ_FMT(3, f_num_frames, "%d");

  ASSERT_EQ_FMT(2, gHeap.root_set_.NumFrames(), "%d");

  {
    RootsFrame _r;
    gList = Alloc<List<int>>();
    gHeap.AddGlobalRoot(gList);
  }
  gList->append(0xbeef);
  ASSERT_EQ(gList->index_(0), 0xbeef);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char **argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(string_collection_test);
  RUN_TEST(list_collection_test);
  RUN_TEST(cycle_collection_test);

  RUN_TEST(root_set_test);
  RUN_TEST(root_set_null_test);
  RUN_TEST(root_set_big_test);

  // RUN_TEST(root_set_stress_test);

  RUN_TEST(rooting_scope_test);

  // f(g(), h()) problem
  // RUN_TEST(old_slice_demo);

#if RET_VAL_ROOTING
  RUN_TEST(new_slice_demo);
#endif

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
