#include <assert.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>   // vprintf

#include "gc_heap.h"
#include "greatest.h"
#include "my_runtime.h"
#include "mylib2.h"  // gBuf

using gc_heap::Alloc;
using gc_heap::Dict;
using gc_heap::gHeap;
using gc_heap::kEmptyString;

GLOBAL_STR(kString1, "food");
GLOBAL_STR(kWithNull, "foo\0bar");

TEST print_test() {
  print(kString1);
  println_stderr(kString1);

  print(kWithNull);
  println_stderr(kWithNull);

  PASS();
}

TEST str_to_int_test() {
  int i;
  bool ok;

  ok = _str_to_int(NewStr("345"), &i, 10);
  ASSERT(ok);
  ASSERT_EQ_FMT(345, i, "%d");

  // Hack to test slicing.  Truncated "345" at "34".
  ok = _str_to_int(NewStr("345", 2), &i, 10);
  ASSERT(ok);
  ASSERT_EQ_FMT(34, i, "%d");

  ok = _str_to_int(NewStr("1234567890"), &i, 10);
  ASSERT(ok);
  ASSERT(i == 1234567890);

  // overflow
  ok = _str_to_int(NewStr("12345678901234567890"), &i, 10);
  ASSERT(!ok);

  // underflow
  ok = _str_to_int(NewStr("-12345678901234567890"), &i, 10);
  ASSERT(!ok);

  // negative
  ok = _str_to_int(NewStr("-123"), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Leading space is OK!
  ok = _str_to_int(NewStr(" -123"), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Trailing space is OK!  NOTE: This fails!
  ok = _str_to_int(NewStr(" -123  "), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Empty string isn't an integer
  ok = _str_to_int(NewStr(""), &i, 10);
  ASSERT(!ok);

  ok = _str_to_int(NewStr("xx"), &i, 10);
  ASSERT(!ok);

  // Trailing garbage
  ok = _str_to_int(NewStr("42a"), &i, 10);
  ASSERT(!ok);

  i = to_int(NewStr("ff"), 16);
  ASSERT(i == 255);

  // strtol allows 0x prefix
  i = to_int(NewStr("0xff"), 16);
  ASSERT(i == 255);

  // TODO: test ValueError here
  // i = to_int(NewStr("0xz"), 16);

  i = to_int(NewStr("0"), 16);
  ASSERT(i == 0);

  i = to_int(NewStr("077"), 8);
  ASSERT_EQ_FMT(63, i, "%d");

  bool caught = false;
  try {
    i = to_int(NewStr("zzz"));
  } catch (ValueError* e) {
    caught = true;
  }
  ASSERT(caught);

  PASS();
}

TEST int_to_str_test() {
  Str* int_str;
  int_str = str((1 << 31) - 1);
  ASSERT(str_equals0("2147483647", int_str));

  int_str = str(-(1 << 31) + 1);
  ASSERT(str_equals0("-2147483647", int_str));

  int int_min = -(1 << 31);
  int_str = str(int_min);
  ASSERT(str_equals0("-2147483648", int_str));

  // Wraps with - sign.  Is this well-defined behavior?
  int_str = str(1 << 31);
  log("i = %s", int_str->data_);

  PASS();
}

TEST str_replace_test() {
  Str* s = kString1->replace(NewStr("o"), NewStr("12"));
  ASSERT(str_equals(NewStr("f1212d"), s));
  print(s);

  // BUG in corner case!
  Str* s2 = NewStr("foo")->replace(NewStr("o"), NewStr("123"));
  ASSERT(str_equals(NewStr("f123123"), s2));
  print(s2);

  Str* s3 = NewStr("foxo")->replace(NewStr("o"), NewStr("123"));
  ASSERT(str_equals(NewStr("f123x123"), s3));
  print(s3);

  Str* s4 = kWithNull->replace(NewStr("a"), NewStr("XX"));
  print(s4);
  // Explicit length because of \0
  ASSERT(str_equals(NewStr("foo\0bXXr", 8), s4));

  PASS();
}

void Print(List<Str*>* parts) {
  log("---");
  log("len = %d", len(parts));
  for (int i = 0; i < len(parts); ++i) {
    printf("%d [", i);
    Str* s = parts->index(i);
    int n = len(s);
    fwrite(s->data_, sizeof(char), n, stdout);
    fputs("]\n", stdout);
  }
}

TEST str_split_test() {
  Str* empty = NewStr("");
  auto sep = NewStr(":");
  auto parts = empty->split(sep);
  ASSERT_EQ(1, len(parts));
  Print(parts);

  parts = (NewStr(":"))->split(sep);
  ASSERT_EQ(2, len(parts));
  ASSERT(str_equals(kEmptyString, parts->index(0)));
  ASSERT(str_equals(kEmptyString, parts->index(1)));
  Print(parts);

  parts = (NewStr("::"))->split(sep);
  ASSERT_EQ(3, len(parts));
  Print(parts);

  parts = (NewStr("a:b"))->split(sep);
  ASSERT_EQ(2, len(parts));
  Print(parts);

  parts = (NewStr("abc:def:"))->split(sep);
  ASSERT_EQ(3, len(parts));
  Print(parts);

  parts = (NewStr(":abc:def:"))->split(sep);
  ASSERT_EQ(4, len(parts));
  Print(parts);

  parts = (NewStr("abc:def:ghi"))->split(sep);
  ASSERT_EQ(3, len(parts));
  Print(parts);

  PASS();
}

TEST str_methods_test() {
  log("char funcs");
  ASSERT(!(NewStr(""))->isupper());
  ASSERT(!(NewStr("a"))->isupper());
  ASSERT((NewStr("A"))->isupper());
  ASSERT((NewStr("AB"))->isupper());

  ASSERT((NewStr("abc"))->isalpha());
  ASSERT((NewStr("3"))->isdigit());
  ASSERT(!(NewStr(""))->isdigit());

  log("slice()");
  ASSERT(str_equals(NewStr("f"), kString1->index(0)));

  ASSERT(str_equals(NewStr("d"), kString1->index(-1)));

  ASSERT(str_equals(NewStr("ood"), kString1->slice(1)));
  ASSERT(str_equals(NewStr("oo"), kString1->slice(1, 3)));
  ASSERT(str_equals(NewStr("oo"), kString1->slice(1, -1)));
  ASSERT(str_equals(NewStr("o"), kString1->slice(-3, -2)));
  ASSERT(str_equals(NewStr("fo"), kString1->slice(-4, -2)));

  log("strip()");
  Str* s2 = NewStr(" abc ");
  ASSERT(str_equals0(" abc", s2->rstrip()));

  Str* s3 = NewStr(" def");
  ASSERT(str_equals0(" def", s3->rstrip()));

  Str* s4 = NewStr("");
  ASSERT(str_equals0("", s4->rstrip()));

  Str* s5 = NewStr("");
  ASSERT(str_equals0("", s5->strip()));

  Str* st1 = (NewStr(" 123 "))->strip();
  ASSERT(str_equals0("123", st1));
  Str* st2 = (NewStr(" 123"))->strip();
  ASSERT(str_equals0("123", st2));
  Str* st3 = (NewStr("123 "))->strip();
  ASSERT(str_equals0("123", st3));

  log("startswith endswith");
  Str* s = NewStr("abc");
  ASSERT(s->startswith(NewStr("")));
  ASSERT(s->startswith(NewStr("ab")));
  ASSERT(s->startswith(s));
  ASSERT(!s->startswith(NewStr("bc")));

  ASSERT(s->endswith(NewStr("")));
  ASSERT(!s->endswith(NewStr("ab")));
  ASSERT(s->endswith(NewStr("bc")));
  ASSERT(s->endswith(s));

  log("rjust()");
  auto space = NewStr(" ");
  auto s6 = NewStr("13");
  ASSERT(str_equals0("  13", s6->rjust(4, space)));
  ASSERT(str_equals0(" 13", s6->rjust(3, space)));
  ASSERT(str_equals0("13", s6->rjust(2, space)));
  ASSERT(str_equals0("13", s6->rjust(1, space)));

  ASSERT(str_equals0("13  ", s6->ljust(4, space)));
  ASSERT(str_equals0("13 ", s6->ljust(3, space)));
  ASSERT(str_equals0("13", s6->ljust(2, space)));
  ASSERT(str_equals0("13", s6->ljust(1, space)));

  log("join()");
  auto foo = NewStr("foo");
  auto bar = NewStr("bar");

  auto L1 = Alloc<List<Str*>>(std::initializer_list<Str*>{foo, bar});
  ASSERT(str_equals(NewStr("foobar"), kEmptyString->join(L1)));

  // Join by NUL
  ASSERT(str_equals(NewStr("foo\0bar", 7), NewStr("\0", 1)->join(L1)));

  auto L2 = Alloc<List<Str*>>(std::initializer_list<Str*>{foo});
  ASSERT(str_equals(NewStr("foo"), kEmptyString->join(L2)));

  auto empty_list = Alloc<List<Str*>>(std::initializer_list<Str*>{});

  auto empty = kEmptyString->join(empty_list);
  ASSERT(str_equals(kEmptyString, empty));
  ASSERT_EQ(0, len(empty));

  auto j1 = (NewStr(" "))->join(empty_list);
  ASSERT(str_equals(kEmptyString, j1));
  ASSERT_EQ(0, len(j1));

  PASS();
}

TEST str_funcs_test() {
  log("str_concat()");
  ASSERT(str_equals(NewStr("foodfood"), str_concat(kString1, kString1)));
  ASSERT(str_equals(kEmptyString, str_concat(kEmptyString, kEmptyString)));

  log("str_repeat()");
  Str* s = NewStr("abc");

  // -1 is allowed by Python and used by Oil!
  ASSERT(str_equals(kEmptyString, str_repeat(s, -1)));
  ASSERT(str_equals(kEmptyString, str_repeat(s, 0)));

  Str* r1 = str_repeat(s, 1);
  ASSERT(str_equals(s, r1));

  Str* r3 = str_repeat(s, 3);
  ASSERT(str_equals(NewStr("abcabcabc"), r3));

  log("repr %s", repr(NewStr(""))->data_);
  log("repr %s", repr(NewStr("'"))->data_);
  log("repr %s", repr(NewStr("'single'"))->data_);
  log("repr %s", repr(NewStr("\"double\""))->data_);

  // this one is truncated
  const char* n_str = "NUL \x00 NUL";
  int n_len = 9;  // 9 bytes long
  log("repr %s", repr(NewStr(n_str, n_len))->data_);
  log("len %d", len(repr(NewStr(n_str, n_len))));

  log("repr %s", repr(NewStr("tab\tline\nline\r\n"))->data_);
  log("repr %s", repr(NewStr("high \xFF \xFE high"))->data_);

  ASSERT_EQ(65, ord(NewStr("A")));
  ASSERT(str_equals(NewStr("A"), chr(65)));

  PASS();
}

TEST str_iters_test() {
  for (StrIter it(kString1); !it.Done(); it.Next()) {
    print(it.Value());
  }

  PASS();
}

TEST list_methods_test() {
  auto init = std::initializer_list<int>{5, 6, 7, 8};
  auto ints = Alloc<List<int>>(init);

  List<int>* slice1 = ints->slice(1);
  ASSERT_EQ(3, len(slice1));
  ASSERT_EQ(6, slice1->index(0));

  List<int>* slice2 = ints->slice(-4, -2);
  ASSERT_EQ(2, len(slice2));
  ASSERT_EQ(5, slice2->index(0));

  log("-- before pop(0)");
  for (int i = 0; i < len(ints); ++i) {
    log("ints[%d] = %d", i, ints->index(i));
  }
  ASSERT_EQ(4, len(ints));  // [5, 6, 7, 8]

  log("pop()");

  ints->pop();  // [5, 6, 7]
  ASSERT_EQ(3, len(ints));
  ASSERT_EQ_FMT(5, ints->index(0), "%d");
  ASSERT_EQ_FMT(6, ints->index(1), "%d");
  ASSERT_EQ_FMT(7, ints->index(2), "%d");

  log("pop(0)");

  ints->pop(0);  // [6, 7]
  ASSERT_EQ(2, len(ints));
  ASSERT_EQ_FMT(6, ints->index(0), "%d");
  ASSERT_EQ_FMT(7, ints->index(1), "%d");

  ints->reverse();
  ASSERT_EQ(2, len(ints));  // [7, 6]

  ASSERT_EQ_FMT(7, ints->index(0), "%d");
  ASSERT_EQ_FMT(6, ints->index(1), "%d");

  ints->append(9);  // [7, 6, 9]
  ASSERT_EQ(3, len(ints));

  ints->reverse();  // [9, 6, 7]
  ASSERT_EQ(9, ints->index(0));
  ASSERT_EQ(6, ints->index(1));
  ASSERT_EQ(7, ints->index(2));

  auto other = Alloc<List<int>>(std::initializer_list<int>{-1, -2});
  ints->extend(other);  // [9, 6, 7, 1, 2]
  ASSERT_EQ(5, len(ints));
  ASSERT_EQ(-2, ints->index(4));
  ASSERT_EQ(-1, ints->index(3));

  ints->clear();
  ASSERT_EQ(0, len(ints));
  ASSERT_EQ(0, ints->slab_->items_[0]);  // make sure it's zero'd

  PASS();
}

void ListFunc(std::initializer_list<Str*> init) {
  log("init.size() = %d", init.size());
}

TEST list_funcs_test() {
  auto L = list_repeat<Str*>(nullptr, 3);
  ASSERT_EQ(3, len(L));

  auto L2 = list_repeat<bool>(true, 3);
  log("list_repeat length = %d", len(L2));
  log("item 0 %d", L2->index(0));
  log("item 1 %d", L2->index(1));

  // Not implemented since we don't use it in Oil.
  // ints->sort();

  PASS();
}

TEST list_iters_test() {
  log("  forward iteration over list");
  auto init = std::initializer_list<int>{1, 2, 3};
  auto ints = Alloc<List<int>>(init);

  for (ListIter<int> it(ints); !it.Done(); it.Next()) {
    int x = it.Value();
    log("x = %d", x);
  }

  log("  backward iteration over list");
  for (ReverseListIter<int> it(ints); !it.Done(); it.Next()) {
    int x = it.Value();
    log("x = %d", x);
  }

  // hm std::initializer_list is "first class"
  auto strs = {NewStr("foo"), NewStr("bar")};
  ListFunc(strs);

  PASS();
}

TEST sort_test() {
  ASSERT_EQ(0, int_cmp(0, 0));
  ASSERT_EQ(-1, int_cmp(0, 5));
  ASSERT_EQ(1, int_cmp(0, -5));

  auto a = NewStr("a");
  auto aa = NewStr("aa");
  auto b = NewStr("b");

  ASSERT_EQ(0, str_cmp(kEmptyString, kEmptyString));
  ASSERT_EQ(-1, str_cmp(kEmptyString, a));
  ASSERT_EQ(-1, str_cmp(a, aa));
  ASSERT_EQ(-1, str_cmp(a, b));

  ASSERT_EQ(1, str_cmp(b, a));
  ASSERT_EQ(1, str_cmp(b, kEmptyString));

  auto strs = Alloc<List<Str*>>();
  strs->append(NewStr("c"));
  strs->append(NewStr("a"));
  strs->append(NewStr("b"));
  strs->append(kEmptyString);
  ASSERT_EQ(4, len(strs));  // ['c', 'a', 'b', '']

#if 0
  strs->sort();  // ['a', 'b', 'c']
  ASSERT_EQ(4, len(strs));
  ASSERT(str_equals(kEmptyString, strs->index(0)));
  ASSERT(str_equals(NewStr("a"), strs->index(1)));
  ASSERT(str_equals(NewStr("b"), strs->index(2)));
  ASSERT(str_equals(NewStr("c"), strs->index(3)));
#endif

  PASS();
}

TEST contains_test() {
  bool b;

  // NOTE: 'substring' in mystr not allowed now, only 'c' in mystr
#if 0
  b = str_contains(NewStr("foo"), NewStr("oo"));
  ASSERT(b == true);

  b = str_contains(NewStr("foo"), NewStr("ood"));
  ASSERT(b == false);
#endif

  b = str_contains(NewStr("foo\0a", 5), NewStr("a"));
  ASSERT(b == true);

  // this ends with a NUL, but also has a NUL terinator.
  Str* s = NewStr("foo\0", 4);
  b = str_contains(s, NewStr("\0", 1));
  ASSERT(b == true);

  log("  List<Str*>");
  auto strs = Alloc<List<Str*>>();
  strs->append(NewStr("bar"));

  b = list_contains(strs, NewStr("foo"));
  ASSERT(b == false);

  strs->append(NewStr("foo"));
  b = list_contains(strs, NewStr("foo"));
  ASSERT(b == true);

  log("  ints");
  auto ints = Alloc<List<int>>(std::initializer_list<int>{1, 2, 3});
  b = list_contains(ints, 1);
  ASSERT(b == true);

  b = list_contains(ints, 42);
  ASSERT(b == false);

  log("  floats");
  auto floats =
      Alloc<List<double>>(std::initializer_list<double>{0.5, 0.25, 0.0});
  b = list_contains(floats, 0.0);
  log("b = %d", b);
  b = list_contains(floats, 42.0);
  log("b = %d", b);

  PASS();
}

TEST dict_methods_test() {
  Dict<int, Str*>* d = Alloc<Dict<int, Str*>>();
  d->set(1, NewStr("foo"));
  ASSERT(str_equals0("foo", d->index(1)));

  auto d2 = Alloc<Dict<Str*, int>>();
  Str* key = NewStr("key");
  d2->set(key, 42);
  ASSERT_EQ(42, d2->index(key));

  d2->set(NewStr("key2"), 2);
  d2->set(NewStr("key3"), 3);

  ASSERT_EQ_FMT(3, len(d2), "%d");

  auto keys = d2->keys();
  ASSERT_EQ_FMT(3, len(keys), "%d");

  // Retain insertion order
  ASSERT(str_equals0("key", keys->index(0)));
  ASSERT(str_equals0("key2", keys->index(1)));
  ASSERT(str_equals0("key3", keys->index(2)));

  auto values = d2->values();
  ASSERT_EQ_FMT(3, len(values), "%d");
  ASSERT_EQ(42, values->index(0));
  ASSERT_EQ(2, values->index(1));
  ASSERT_EQ(3, values->index(2));

  d2->clear();
  ASSERT_EQ(0, len(d2));
  // Ensure it was zero'd
  ASSERT_EQ(nullptr, d2->keys_->items_[0]);
  ASSERT_EQ(0, d2->values_->items_[0]);

  // get()
  ASSERT(str_equals0("foo", d->get(1)));

  // dict_contains()
  ASSERT(dict_contains(d, 1));
  ASSERT(!dict_contains(d, 2));

  ASSERT_EQ(nullptr, d->get(423));  // nonexistent

  // get(k, default)
  ASSERT_EQ(kEmptyString, d->get(423, kEmptyString));
  ASSERT_EQ(-99, d2->get(kEmptyString, -99));

  // sorted()
  auto d3 = Alloc<Dict<Str*, int>>();
  auto a = NewStr("a");

  d3->set(NewStr("b"), 11);
  d3->set(NewStr("c"), 12);
  d3->set(NewStr("a"), 10);
  ASSERT_EQ(10, d3->index(NewStr("a")));
  ASSERT_EQ(11, d3->index(NewStr("b")));
  ASSERT_EQ(12, d3->index(NewStr("c")));
  ASSERT_EQ(3, len(d3));

#if 0
  auto keys3 = sorted(d3);
  ASSERT_EQ(3, len(keys3));
  ASSERT(str_equals0("a", keys3->index(0)));
  ASSERT(str_equals0("b", keys3->index(1)));
  ASSERT(str_equals0("c", keys3->index(2)));
#endif

  auto keys4 = d3->keys();
  ASSERT(list_contains(keys4, a));
  ASSERT(!list_contains(keys4, NewStr("zzz")));

  ASSERT(dict_contains(d3, a));
  mylib::dict_remove(d3, a);
  ASSERT(!dict_contains(d3, a));
  ASSERT_EQ(2, len(d3));

  // TODO: keys() and values() need to respect deletions

  PASS();
}

TEST dict_funcs_test() {
  PASS();
}

TEST dict_iters_test() {
  auto d2 = Alloc<Dict<Str*, int>>();
  d2->set(NewStr("foo"), 2);
  d2->set(NewStr("bar"), 3);

  auto keys = d2->keys();
  for (int i = 0; i < len(keys); ++i) {
    printf("k %s\n", keys->index(i)->data_);
  }

  log("  iterating over Dict");
  for (DictIter<Str*, int> it(d2); !it.Done(); it.Next()) {
    log("k = %s, v = %d", it.Key()->data_, it.Value());
  }

  PASS();
}

TEST formatter_test() {
  gBuf.reset();
  gBuf.write_const("[", 1);
  gBuf.format_s(NewStr("bar"));
  gBuf.write_const("]", 1);
  log("value = %s", gBuf.getvalue()->data_);

  gBuf.format_d(42);
  gBuf.write_const("-", 1);
  gBuf.format_d(42);
  gBuf.write_const(".", 1);
  log("value = %s", gBuf.getvalue()->data_);

  PASS();
}

GLOBAL_STR(b, "b");
GLOBAL_STR(bb, "bx");

TEST collect_test() {
  gHeap.Init(1 << 8);  // 1 KiB

  auto s = NewStr("abcdefg");
  int total = 0;
  for (int i = 0; i < 40; ++i) {
    s = s->replace(b, bb);
    total += len(s);

    // hit NUL termination path
    s = NewStr("NUL");
    total += len(s);

    // log("i = %d", i);
    // log("len(s) = %d", len(s));
  }
  log("total = %d", total);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(print_test);
  RUN_TEST(str_to_int_test);
  RUN_TEST(int_to_str_test);
  RUN_TEST(str_replace_test);
  RUN_TEST(str_split_test);
  RUN_TEST(str_methods_test);
  RUN_TEST(str_funcs_test);
  RUN_TEST(str_iters_test);
  RUN_TEST(list_methods_test);
  RUN_TEST(list_funcs_test);
  RUN_TEST(list_iters_test);
  RUN_TEST(sort_test);
  RUN_TEST(contains_test);
  RUN_TEST(dict_methods_test);
  RUN_TEST(dict_funcs_test);
  RUN_TEST(dict_iters_test);

  RUN_TEST(formatter_test);
  RUN_TEST(collect_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
