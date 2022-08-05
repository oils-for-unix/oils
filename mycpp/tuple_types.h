#ifndef TUPLE_TYPES_H
#define TUPLE_TYPES_H

template <class A, class B>
class Tuple2 {
 public:
  Tuple2(A a, B b) : a_(a), b_(b) {
  }
  A at0() {
    return a_;
  }
  B at1() {
    return b_;
  }

 private:
  A a_;
  B b_;
};

template <class A, class B, class C>
class Tuple3 {
 public:
  Tuple3(A a, B b, C c) : a_(a), b_(b), c_(c) {
  }
  A at0() {
    return a_;
  }
  B at1() {
    return b_;
  }
  C at2() {
    return c_;
  }

 private:
  A a_;
  B b_;
  C c_;
};

template <class A, class B, class C, class D>
class Tuple4 {
 public:
  Tuple4(A a, B b, C c, D d) : a_(a), b_(b), c_(c), d_(d) {
  }
  A at0() {
    return a_;
  }
  B at1() {
    return b_;
  }
  C at2() {
    return c_;
  }
  D at3() {
    return d_;
  }

 private:
  A a_;
  B b_;
  C c_;
  D d_;
};

#endif
