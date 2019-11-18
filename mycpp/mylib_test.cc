#include <stdarg.h>  // va_list, etc.
#include <stdio.h>  // vprintf
#include <assert.h>

#include "mylib.h"

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

void test_str_funcs() {
  assert((new Str("abc"))->isalpha());

  Str* s = new Str("abc");
  Str* r0 = str_repeat(s, 0);
  Str* r1 = str_repeat(s, 1);
  Str* r3 = str_repeat(s, 3);
  log("r0 = %s", r0->data_);
  log("r1 = %s", r1->data_);
  log("r3 = %s", r3->data_);

  Str* int_str;
  int_str = str((1<<31) - 1);
  log("i = %s", int_str->data_);

  // wraps with - sign
  int_str = str(1<<31);
  log("i = %s", int_str->data_);

  int_str = str(-(1<<31) + 1);
  log("i = %s", int_str->data_);
  int_str = str(-(1<<31));
  log("i = %s", int_str->data_);
}

using mylib::BufLineReader;

void test_buf_line_reader() {
  Str* s = new Str("foo\nbar\nleftover");
  BufLineReader* reader = new BufLineReader(s);
  Str* line;

  log("BufLineReader");

  line = reader->readline();
  log("1 [%s]", line->data_);
  line = reader->readline();
  log("2: [%s]", line->data_);
  line = reader->readline();
  log("3: [%s]", line->data_);
  line = reader->readline();
  log("4: [%s]", line->data_);
}

void test_formatter() {
  gBuf.reset();
  gBuf.write_const("[", 1);
  gBuf.format_s(new Str("bar"));
  gBuf.write_const("]", 1);
  log("value = %s", gBuf.getvalue()->data_);

  gBuf.format_d(42);
  gBuf.write_const("-", 1);
  gBuf.format_d(42);
  gBuf.write_const(".", 1);
  log("value = %s", gBuf.getvalue()->data_);
}

void test_contains() {
  bool b;

  b = str_contains(new Str("foo"), new Str("oo"));
  log("b = %d", b);

  b = str_contains(new Str("foo"), new Str("ood"));
  log("b = %d", b);

  log("  strs");
  auto strs = new List<Str*>();
  strs->append(new Str("bar"));

  b = list_contains(strs, new Str("foo"));
  log("b = %d", b);
  strs->append(new Str("foo"));
  b = list_contains(strs, new Str("foo"));
  log("b = %d", b);

  log("  ints");
  auto ints = new List<int>({1, 2, 3});
  b = list_contains(ints, 1);
  log("b = %d", b);
  b = list_contains(ints, 42);
  log("b = %d", b);

  log("  floats");
  auto floats = new List<double>({0.5, 0.25, 0.0});
  b = list_contains(floats, 0.0);
  log("b = %d", b);
  b = list_contains(floats, 42.0);
  log("b = %d", b);
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
  test_str_funcs();

  log("");
  Dict<int, Str*>* d = new Dict<int, Str*>();
  (*d)[1] = new Str("foo");
  log("d[1] = %s", d->index(1)->data_);

  log("");
  test_buf_line_reader();

  log("");
  test_formatter();

  log("");
  test_contains();
}

