#include "mylib2.h"

#include "gc_heap.h"
#include "greatest.h"
#include "my_runtime.h"

using gc_heap::NewStr;
using gc_heap::StackRoots;
using gc_heap::kEmptyString;

TEST split_once_test() {
  log("split_once()");

  Str* s = nullptr;
  Str* delim = nullptr;
  StackRoots _roots1({&s, &delim});

  s = NewStr("foo=bar");
  delim = NewStr("=");
  Tuple2<Str*, Str*> t = mylib::split_once(s, delim);

  auto t0 = t.at0();
  auto t1 = t.at1();

  log("t %p %p", t0, t1);

  Str* foo = nullptr;
  StackRoots _roots2({&t0, &t1, &foo});
  foo = NewStr("foo");

  // ASSERT(str_equals(t0, NewStr("foo")));
  // ASSERT(str_equals(t1, NewStr("bar")));

  PASS();

  Tuple2<Str*, Str*> u = mylib::split_once(NewStr("foo="), NewStr("="));
  ASSERT(str_equals(u.at0(), NewStr("foo")));
  ASSERT(str_equals(u.at1(), NewStr("")));

  Tuple2<Str*, Str*> v = mylib::split_once(NewStr("foo="), NewStr("Z"));
  ASSERT(str_equals(v.at0(), NewStr("foo=")));
  ASSERT(v.at1() == nullptr);

  Tuple2<Str*, Str*> w = mylib::split_once(NewStr(""), NewStr("Z"));
  ASSERT(str_equals(w.at0(), NewStr("")));
  ASSERT(w.at1() == nullptr);

  PASS();
}

TEST int_to_str_test() {
  int int_min = -(1 << 31);
  Str* int_str;

  int_str = mylib::hex_lower(15);
  ASSERT(str_equals0("f", int_str));
  print(int_str);
  print(mylib::hex_lower(int_min));

  int_str = mylib::hex_upper(15);
  ASSERT(str_equals0("F", int_str));
  print(mylib::hex_upper(int_min));

  int_str = mylib::octal(15);
  ASSERT(str_equals0("17", int_str));
  print(mylib::octal(int_min));

  PASS();
}

TEST writer_test() {
  // Demonstrate bug with inheritance
  log("obj obj_len %d", offsetof(gc_heap::Obj, obj_len_));
  log("buf obj_len %d", offsetof(mylib::BufWriter, obj_len_));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gc_heap::gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(split_once_test);
  RUN_TEST(int_to_str_test);
  RUN_TEST(writer_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
