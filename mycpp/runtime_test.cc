#include <stdarg.h>  // va_list, etc.
#include <stdio.h>  // vprintf
#include <assert.h>

#include "runtime.h"

void test_str_to_int() {
  int i;
  bool ok;
 
  ok = _str_to_int(new Str("345"), &i);
  assert(ok);
  assert(i == 345);

  // TODO: Is there a way to check for overflow?
  // strtol returns 'long int'.
  ok = _str_to_int(new Str("1234567890"), &i);
  assert(ok);
  log("i = %d", i);
  assert(i == 1234567890);

  // negative
  ok = _str_to_int(new Str("-123"), &i);
  assert(ok);
  assert(i == -123);

  // Leading space is OK!
  ok = _str_to_int(new Str(" -123"), &i);
  assert(ok);
  assert(i == -123);

  // Trailing space is OK!  NOTE: This fails!
  ok = _str_to_int(new Str(" -123  "), &i);
  assert(ok);
  assert(i == -123);

  // Empty string isn't an integer
  ok = _str_to_int(new Str(""), &i);
  assert(!ok);

  ok = _str_to_int(new Str("xx"), &i);
  assert(!ok);

  // Trailing garbage
  ok = _str_to_int(new Str("42a"), &i);
  assert(!ok);
}

void test_str_methods() {
  assert((new Str("abc"))->isalpha());
}

int main(int argc, char **argv) {
  List<int>* L = new List<int> {1, 2, 3};

  // TODO: How to do this?

  // Dict d {{"key", 1}, {"val", 2}};

  log("size: %d", len(L));
  log("");

  Tuple2<int, int>* t2 = new Tuple2<int, int>(5, 6);
  log("t2[0] = %d", t2->at0());
  log("t2[1] = %d", t2->at1());

  Tuple2<int, Str*>* u2 = new Tuple2<int, Str*>(42, new Str("hello"));
  log("u2[0] = %d", u2->at0());
  log("u2[1] = %s", u2->at1()->data_);

  log("");

  auto t3 = new Tuple3<int, Str*, Str*>(42, new Str("hello"), new Str("bye"));
  log("t3[0] = %d", t3->at0());
  log("t3[1] = %s", t3->at1()->data_);
  log("t3[2] = %s", t3->at2()->data_);

  log("");

  auto t4 = new Tuple4<int, Str*, Str*, int>(
      42, new Str("4"), new Str("four"), -42);

  log("t4[0] = %d", t4->at0());
  log("t4[1] = %s", t4->at1()->data_);
  log("t4[2] = %s", t4->at2()->data_);
  log("t4[3] = %d", t4->at3());

  test_str_to_int();
  test_str_methods();
}
