#ifdef OLDSTL_BINDINGS
  // clang-format off
  #include "mycpp/oldstl_containers.h"
  #include "mycpp/oldstl_builtins.h"
  #include "mycpp/oldstl_mylib.h"
// clang-format on
#else
  #include "mycpp/gc_mylib.h"
#endif

#include "vendor/greatest.h"

TEST test_mylib_funcs() {
  Str* int_str;

  int int_min = INT_MIN;

  int_str = mylib::hex_lower(15);
  ASSERT(str_equals0("f", int_str));
  print(mylib::hex_lower(int_min));  // ASAN implicitly checks this

  int_str = mylib::hex_upper(15);
  ASSERT(str_equals0("F", int_str));
  print(mylib::hex_upper(int_min));  // ASAN

  int_str = mylib::octal(15);
  ASSERT(str_equals0("17", int_str));
  print(mylib::octal(int_min));  // ASAN

  log("split_once()");
  Tuple2<Str*, Str*> t = mylib::split_once(StrFromC("foo=bar"), StrFromC("="));
  ASSERT(str_equals(t.at0(), StrFromC("foo")));
  ASSERT(str_equals(t.at1(), StrFromC("bar")));

  Tuple2<Str*, Str*> u = mylib::split_once(StrFromC("foo="), StrFromC("="));
  ASSERT(str_equals(u.at0(), StrFromC("foo")));
  ASSERT(str_equals(u.at1(), StrFromC("")));

  Tuple2<Str*, Str*> v = mylib::split_once(StrFromC("foo="), StrFromC("Z"));
  ASSERT(str_equals(v.at0(), StrFromC("foo=")));
  ASSERT(v.at1() == nullptr);

  Tuple2<Str*, Str*> w = mylib::split_once(StrFromC(""), StrFromC("Z"));
  ASSERT(str_equals(w.at0(), StrFromC("")));
  ASSERT(w.at1() == nullptr);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(test_mylib_funcs);

  GREATEST_MAIN_END();
  return 0;
}
