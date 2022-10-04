// smartptr_test.cc -- OLD UNUSED CODE

#include "mycpp/smartptr.h"

#include "vendor/greatest.h"

Str* myfunc() {
  Local<Str> str1(StrFromC("foo"));
  Local<Str> str2(StrFromC("foo"));
  Local<Str> str3(StrFromC("foo"));

#if 0
  log("myfunc roots_top = %d", gHeap.roots_top_);
  ShowRoots(gHeap);
#endif

  return str1;  // implicit conversion to raw pointer
}

void otherfunc(Local<Str> s) {
  log("otherfunc roots_top_ = %d", gHeap.roots_.size());
  log("len(s) = %d", len(s));
}

void paramfunc(Param<Str> s) {
  log("paramfunc roots_top_ = %d", gHeap.roots_.size());
  log("len(s) = %d", len(s));
}

#if 0
TEST local_test() {
  gHeap.Init();  // reset the whole thing

  {
    log("top = %d", gHeap.roots_top_);
    ASSERT_EQ(0, gHeap.roots_top_);

    auto point = Alloc<Point>(3, 4);
    Local<Point> p(point);
    ASSERT_EQ(1, gHeap.roots_top_);

    log("point.x = %d", p->x_);  // invokes operator->

    // invokes operator*, but I don't think we need it!
    // log("point.y = %d", (*p).y_);

    Local<Str> str2(StrFromC("bar"));
    ASSERT_EQ(2, gHeap.roots_top_);

    myfunc();

    otherfunc(str2);
    ASSERT_EQ_FMT(2, gHeap.roots_top_, "%d");

    paramfunc(str2);
    ASSERT_EQ_FMT(2, gHeap.roots_top_, "%d");

    ShowRoots(gHeap);

    gHeap.Collect();

    // This uses implicit convertion from T* to Local<T>, which is OK!  Reverse
    // is not OK.
    Local<Point> p2 = point;
    ASSERT_EQ_FMT(3, gHeap.roots_top_, "%d");

    Local<Point> p3;
    ASSERT_EQ_FMT(3, gHeap.roots_top_, "%d");
    p3 = p2;
    ASSERT_EQ_FMT(4, gHeap.roots_top_, "%d");
  }
  ASSERT_EQ_FMT(0, gHeap.roots_top_, "%d");

  // Hm this calls copy constructor!
  Local<Point> p4 = nullptr;

  Param<Point> p5 = p4;

  PASS();
}
#endif

class Base {
 public:
  explicit Base(int a) : a_(a) {
  }
  int a_;
};

class Derived : public Base {
 public:
  Derived(int a, int b) : Base(a), b_(b) {
  }
  int b_;
};

int base_func(Base* base) {
  return base->a_;
}

int base_func_local(Local<Base> base) {
  return base->a_;
}

#if 0
TEST local_variance_test() {
  Base i1(5);
  log("i1.a_ = %d", i1.a_);

  Derived i2(3, 4);
  log("i2 = %d %d", i2.a_, i2.b_);

  ASSERT_EQ(5, base_func(&i1));
  ASSERT_EQ(3, base_func(&i2));

  Local<Base> h1 = &i1;
  // Does NOT work
  // Local<Base> h2 = i2;
  Local<Derived> h2 = &i2;

  ASSERT_EQ(5, base_func_local(h1));
  // Variance doesn't work!  Bad!  So we don't want to use Local<T>.
  // ASSERT_EQ(3, base_func_local(h2));

  PASS();
}
#endif

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

#if 0
  RUN_TEST(local_variance_test);
  RUN_TEST(local_test);
#endif

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
