#include "mycpp/runtime.h"
#include "vendor/greatest.h"

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

GREATEST_MAIN_DEFS();

int main(int argc, char **argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(tuple_field_masks_test);
  RUN_TEST(tuple_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
