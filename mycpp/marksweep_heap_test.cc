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

TEST tuple_field_masks_test() {
  Tuple2<Str *, Str *> ss(nullptr, nullptr);
  ASSERT_EQ_FMT(0b11, ss.field_mask_, "%d");

  // 8 + 4 on 64 bit
  Tuple2<Str *, int> si(nullptr, 42);
  ASSERT_EQ_FMT(0b01, si.field_mask_, "%d");

  // 4 + 8 on 64 bit
  Tuple2<int, Str *> is(42, nullptr);
  ASSERT_EQ_FMT(0b10, is.field_mask_, "%d");

  Tuple3<Str *, Str *, Str *> sss(nullptr, nullptr, nullptr);
  ASSERT_EQ_FMT(0b111, sss.field_mask_, "%d");

  Tuple3<int, Str *, Str *> iss(42, nullptr, nullptr);
  ASSERT_EQ_FMT(0b110, iss.field_mask_, "%d");

  // 4 + 4 + 8 + 8, so it's 0b110 not 0b1100
  Tuple4<int, int, Str *, Str *> iiss(42, 42, nullptr, nullptr);
  ASSERT_EQ_FMT(0b110, iiss.field_mask_, "%d");

  PASS();
}

TEST tuple_test() {
  gHeap.Collect();
  printf("\n");

  Tuple2<int, Tuple2<int, Str *> *> *t3 = nullptr;
  StackRoots _roots2({&t3});

  {
    Tuple2<int, int> *t0 = nullptr;
    Tuple2<int, Str *> *t1 = nullptr;
    Tuple2<int, Str *> *t2 = nullptr;

    Str *str0 = nullptr;
    Str *str1 = nullptr;

    StackRoots _roots({&str0, &str1, &t0, &t1, &t2});

    gHeap.Collect();

    str0 = StrFromC("foo_0");
    gHeap.Collect();

    str1 = StrFromC("foo_1");

    gHeap.Collect();

    t0 = Alloc<Tuple2<int, int>>(2, 3);

    gHeap.Collect();

    printf("%s\n", str0->data_);
    printf("%s\n", str1->data_);

    t1 = Alloc<Tuple2<int, Str *>>(4, str0);
    t2 = Alloc<Tuple2<int, Str *>>(5, str1);

    gHeap.Collect();

    printf("%s\n", str0->data_);
    printf("%s\n", str1->data_);

    printf("%d = %d\n", t0->at0(), t0->at1());
    printf("%d = %s\n", t1->at0(), t1->at1()->data_);
    printf("%d = %s\n", t2->at0(), t2->at1()->data_);

    gHeap.Collect();

    t3 = Alloc<Tuple2<int, Tuple2<int, Str *> *>>(6, t2);

    gHeap.Collect();
  }

  printf("%d = { %d = %s }\n", t3->at0(), t3->at1()->at0(),
         t3->at1()->at1()->data_);

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

  r.PushScope();  // main() call
  ASSERT_EQ_FMT(0, r.NumRoots(), "%d");
  ASSERT_EQ_FMT(2, r.NumFrames(), "%d");

  r.PushScope();  // g() call
  ASSERT_EQ_FMT(0, r.NumRoots(), "%d");
  ASSERT_EQ_FMT(3, r.NumFrames(), "%d");

  // g() returns "X"
  r.RootOnReturn(StrFromC("X"));
  ASSERT_EQ_FMT(1, r.NumRoots(), "%d");
  ASSERT_EQ_FMT(3, r.NumFrames(), "%d");
  ASSERT_EQ_FMT(1, static_cast<int>(r.stack_[1].size()), "%d");
  ASSERT_EQ_FMT(0, static_cast<int>(r.stack_[2].size()), "%d");

  r.PopScope();  // g() return
  // "X" is still live after foo() returns!
  ASSERT_EQ_FMT(1, r.NumRoots(), "%d");
  ASSERT_EQ_FMT(2, r.NumFrames(), "%d");
  ASSERT_EQ_FMT(1, static_cast<int>(r.stack_[1].size()), "%d");

  r.PushScope();  // another g() call
  ASSERT_EQ_FMT(1, r.NumRoots(), "%d");
  ASSERT_EQ_FMT(3, r.NumFrames(), "%d");

  // g() returns "X" again
  r.RootOnReturn(StrFromC("X"));
  ASSERT_EQ_FMT(2, r.NumRoots(), "%d");
  ASSERT_EQ_FMT(3, r.NumFrames(), "%d");
  ASSERT_EQ_FMT(2, static_cast<int>(r.stack_[1].size()), "%d");
  ASSERT_EQ_FMT(0, static_cast<int>(r.stack_[2].size()), "%d");

  r.PopScope();  // another g() return
  ASSERT_EQ_FMT(2, r.NumRoots(), "%d");
  ASSERT_EQ_FMT(2, r.NumFrames(), "%d");
  ASSERT_EQ_FMT(2, static_cast<int>(r.stack_[1].size()), "%d");

  r.PopScope();  // main() return
  ASSERT_EQ_FMT(1, r.NumFrames(), "%d");
  ASSERT_EQ_FMT(0, r.NumRoots(), "%d");

  PASS();
}

TEST root_set_null_test() {
  RootSet r(32);

  r.PushScope();
  r.PushScope();

  r.RootOnReturn(StrFromC("X"));
  ASSERT_EQ_FMT(1, r.NumRoots(), "%d");

  // Does NOT get added
  r.RootOnReturn(nullptr);
  ASSERT_EQ_FMT(1, r.NumRoots(), "%d");

  r.PopScope();
  r.PopScope();

  PASS();
}

TEST root_set_big_test() {
  Str *s = StrFromC("Y");

  RootSet r(32);
  // Test many frames
  r.PushScope();
  for (int i = 0; i < 100; ++i) {
    // log("i %d", i);
    r.PushScope();
    for (int j = 0; j < 100; ++j) {
      r.RootOnReturn(s);
    }
  }

  PASS();
}

int f() {
  RootingScope r2;

  // Can't assert in this non-test function
  return gHeap.root_set_.NumFrames();
}

Str *g(Str *left, Str *right) {
  RootingScope _r;

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

// Like the above, but instead of rooting variables, we create a RootingScope
// instance.  It doesn't return a heap-allocated object, so we don't need
// gHeap.RootOnReturn(). Functions that allocate like Alloc<T> are responsible
// for that.

int count_new(Str *a, Str *b) {
  RootingScope _r;

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
  RootingScope _r;

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
  RootingScope _r;

  for (int i = 0; i < 10; ++i) {
    // NewStr needs to root; also needs RootingScope
    Str *s = StrFromC("abcdef");

    // slice() needs to root; also eneds RootingScope
    Str *t = g(s->slice(1), s->slice(2));

    log("t = %s", t->data());
  }

  PASS();
}

TEST rooting_scope_test() {
  ASSERT_EQ_FMT(1, gHeap.root_set_.NumFrames(), "%d");

  RootingScope r1;
  ASSERT_EQ_FMT(2, gHeap.root_set_.NumFrames(), "%d");

  int f_num_frames = f();
  ASSERT_EQ_FMT(3, f_num_frames, "%d");

  ASSERT_EQ_FMT(2, gHeap.root_set_.NumFrames(), "%d");

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char **argv) {
  gHeap.Init();

  PRINT_GC_MODE_STRING();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(string_collection_test);
  RUN_TEST(list_collection_test);
  RUN_TEST(cycle_collection_test);

  RUN_TEST(tuple_test);
  RUN_TEST(tuple_field_masks_test);

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
