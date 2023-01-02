#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST tuple_field_masks_test() {
  Tuple2<Str *, Str *> ss(nullptr, nullptr);
  ASSERT_EQ_FMT(0b11, FIELD_MASK(ss.header_), "%d");

  // 8 + 4 on 64 bit
  Tuple2<Str *, int> si(nullptr, 42);
  ASSERT_EQ_FMT(0b01, FIELD_MASK(si.header_), "%d");

  // 4 + 8 on 64 bit
  Tuple2<int, Str *> is(42, nullptr);
  ASSERT_EQ_FMT(0b10, FIELD_MASK(is.header_), "%d");

  Tuple3<Str *, Str *, Str *> sss(nullptr, nullptr, nullptr);
  ASSERT_EQ_FMT(0b111, FIELD_MASK(sss.header_), "%d");

  Tuple3<int, Str *, Str *> iss(42, nullptr, nullptr);
  ASSERT_EQ_FMT(0b110, FIELD_MASK(iss.header_), "%d");

  // 4 + 4 + 8 + 8, so it's 0b110 not 0b1100
  Tuple4<int, int, Str *, Str *> iiss(42, 42, nullptr, nullptr);
  ASSERT_EQ_FMT(0b110, FIELD_MASK(iiss.header_), "%d");

  PASS();
}

TEST tuple234_test() {
  Tuple2<int, int> *t2 = Alloc<Tuple2<int, int>>(5, 6);
  log("t2[0] = %d", t2->at0());
  log("t2[1] = %d", t2->at1());

  Tuple2<int, Str *> *u2 = Alloc<Tuple2<int, Str *>>(42, StrFromC("hello"));
  log("u2[0] = %d", u2->at0());
  log("u2[1] = %s", u2->at1()->data_);

  log("");

  auto t3 =
      Alloc<Tuple3<int, Str *, Str *>>(42, StrFromC("hello"), StrFromC("bye"));
  log("t3[0] = %d", t3->at0());
  log("t3[1] = %s", t3->at1()->data_);
  log("t3[2] = %s", t3->at2()->data_);

  log("");

  auto t4 = Alloc<Tuple4<int, Str *, Str *, int>>(42, StrFromC("4"),
                                                  StrFromC("four"), -42);

  log("t4[0] = %d", t4->at0());
  log("t4[1] = %s", t4->at1()->data_);
  log("t4[2] = %s", t4->at2()->data_);
  log("t4[3] = %d", t4->at3());

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

GREATEST_MAIN_DEFS();

int main(int argc, char **argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(tuple_field_masks_test);
  RUN_TEST(tuple234_test);
  RUN_TEST(tuple_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
