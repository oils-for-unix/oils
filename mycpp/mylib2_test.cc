#include "mylib2.h"

#include "greatest.h"
#include "gc_heap.h"
#include "my_runtime.h"

using gc_heap::NewStr;
using gc_heap::kEmptyString;

TEST split_once_test() {
  log("split_once()");
  Tuple2<Str*, Str*> t = mylib::split_once(NewStr("foo=bar"), NewStr("="));
  ASSERT(str_equals(t.at0(), NewStr("foo")));
  ASSERT(str_equals(t.at1(), NewStr("bar")));

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

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gc_heap::gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(split_once_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
