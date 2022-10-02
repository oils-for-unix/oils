#ifndef TUPLE_TYPES_H
#define TUPLE_TYPES_H

// Note:
//
// - These use OBJ_HEADER() instead of inheriting from Obj, because Obj can't
//   be returned by value.  mycpp generates code that returns TupleN<> VALUES,
//   not references (to reduce GC pressure).

template <class A, class B>
class Tuple2 {
 public:
  Tuple2(A a, B b) : a_(a), b_(b) {
    heap_tag_ = Tag::FixedSize;
    typedef Tuple2<A, B> this_type;
    constexpr int m =
        (std::is_pointer<A>() ? maskbit(offsetof(this_type, a_)) : 0) |
        (std::is_pointer<B>() ? maskbit(offsetof(this_type, b_)) : 0);
    field_mask_ = m;
  }

  A at0() {
    return a_;
  }
  B at1() {
    return b_;
  }

  OBJ_HEADER();

 private:
  A a_;
  B b_;
};

template <class A, class B, class C>
class Tuple3 {
 public:
  Tuple3(A a, B b, C c) : a_(a), b_(b), c_(c) {
    heap_tag_ = Tag::FixedSize;
    typedef Tuple3<A, B, C> this_type;
    constexpr int m =
        (std::is_pointer<A>() ? maskbit(offsetof(this_type, a_)) : 0) |
        (std::is_pointer<B>() ? maskbit(offsetof(this_type, b_)) : 0) |
        (std::is_pointer<C>() ? maskbit(offsetof(this_type, c_)) : 0);
    field_mask_ = m;
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

  OBJ_HEADER();

 private:
  A a_;
  B b_;
  C c_;
};

template <class A, class B, class C, class D>
class Tuple4 {
 public:
  Tuple4(A a, B b, C c, D d) : a_(a), b_(b), c_(c), d_(d) {
    heap_tag_ = Tag::FixedSize;
    typedef Tuple4<A, B, C, D> this_type;
    constexpr int m =
        (std::is_pointer<A>() ? maskbit(offsetof(this_type, a_)) : 0) |
        (std::is_pointer<B>() ? maskbit(offsetof(this_type, b_)) : 0) |
        (std::is_pointer<C>() ? maskbit(offsetof(this_type, c_)) : 0) |
        (std::is_pointer<D>() ? maskbit(offsetof(this_type, d_)) : 0);
    field_mask_ = m;
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

  OBJ_HEADER();

 private:
  A a_;
  B b_;
  C c_;
  D d_;
};

#endif
