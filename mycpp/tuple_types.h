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
  Tuple2(A a, B b) : a_(a), b_(b)
  {
    heap_tag_ = Tag::FixedSize;
    field_mask_ = 0;
    field_mask_ |= std::is_pointer<A>() ? maskbit(offsetof( Tuple2<A COMMA B> , a_)) : 0;
    field_mask_ |= std::is_pointer<B>() ? maskbit(offsetof( Tuple2<A COMMA B> , b_)) : 0;
  }

  A at0() {
    return a_;
  }
  B at1() {
    return b_;
  }

 private:
  OBJ_HEADER();
  A a_;
  B b_;
};

template <class A, class B, class C>
class Tuple3 {
 public:
  Tuple3(A a, B b, C c) : a_(a), b_(b), c_(c) {
    heap_tag_ = Tag::FixedSize;
    field_mask_ = 0;
    field_mask_ |= std::is_pointer<A>() ? maskbit(offsetof( Tuple3<A COMMA B COMMA C> , a_)) : 0;
    field_mask_ |= std::is_pointer<B>() ? maskbit(offsetof( Tuple3<A COMMA B COMMA C> , b_)) : 0;
    field_mask_ |= std::is_pointer<C>() ? maskbit(offsetof( Tuple3<A COMMA B COMMA C> , c_)) : 0;
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
  OBJ_HEADER();
  A a_;
  B b_;
  C c_;
};

template <class A, class B, class C, class D>
class Tuple4 {
 public:
  Tuple4(A a, B b, C c, D d) : a_(a), b_(b), c_(c), d_(d) {
    heap_tag_ = Tag::FixedSize;
    field_mask_ = 0;
    field_mask_ |= std::is_pointer<A>() ? maskbit(offsetof( Tuple4<A COMMA B COMMA C COMMA D> , a_)) : 0;
    field_mask_ |= std::is_pointer<B>() ? maskbit(offsetof( Tuple4<A COMMA B COMMA C COMMA D> , b_)) : 0;
    field_mask_ |= std::is_pointer<C>() ? maskbit(offsetof( Tuple4<A COMMA B COMMA C COMMA D> , c_)) : 0;
    field_mask_ |= std::is_pointer<D>() ? maskbit(offsetof( Tuple4<A COMMA B COMMA C COMMA D> , d_)) : 0;
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
  OBJ_HEADER();
  A a_;
  B b_;
  C c_;
  D d_;
};

#endif
