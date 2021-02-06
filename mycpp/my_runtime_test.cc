#include <assert.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>   // vprintf

#include "gc_heap.h"
#include "greatest.h"
#include "my_runtime.h"
#include "mylib2.h"  // gBuf

using gc_heap::Alloc;
using gc_heap::Dict;
using gc_heap::NewList;
using gc_heap::StackRoots;
using gc_heap::gHeap;
using gc_heap::kEmptyString;

GLOBAL_STR(kStrFood, "food");
GLOBAL_STR(kWithNull, "foo\0bar");
GLOBAL_STR(kSpace, " ");

TEST print_test() {
  print(kStrFood);
  println_stderr(kStrFood);

  print(kWithNull);
  println_stderr(kWithNull);

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

GLOBAL_STR(kStrFoo, "foo");
GLOBAL_STR(kStrBar, "bar");
GLOBAL_STR(a, "a");
GLOBAL_STR(XX, "XX");

TEST str_replace_test() {
  Str* o = nullptr;
  Str* _12 = nullptr;
  Str* _123 = nullptr;
  Str* s = nullptr;
  Str* foxo = nullptr;
  StackRoots _roots({&o, &_12, &_123, &s, &foxo});

  o = NewStr("o");
  _12 = NewStr("12");
  _123 = NewStr("123");

  s = kStrFood->replace(o, _12);
  ASSERT(str_equals(NewStr("f1212d"), s));
  print(s);

  s = kStrFoo->replace(o, _123);
  ASSERT(str_equals(NewStr("f123123"), s));
  print(s);

  foxo = NewStr("foxo");
  s = foxo->replace(o, _123);
  ASSERT(str_equals(NewStr("f123x123"), s));
  print(s);

  s = kWithNull->replace(a, XX);
  print(s);

  // Explicit length because of \0
  ASSERT(str_equals(NewStr("foo\0bXXr", 8), s));

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
  Str* sep = nullptr;
  List<Str*>* parts = nullptr;

  StackRoots _roots({&sep, &parts});
  sep = NewStr(":");

  parts = kEmptyString->split(sep);
  ASSERT_EQ(1, len(parts));
  Print(parts);

  parts = (NewStr(":"))->split(sep);
  ASSERT_EQ_FMT(2, len(parts), "%d");
  ASSERT(str_equals(kEmptyString, parts->index(0)));
  ASSERT(str_equals(kEmptyString, parts->index(1)));
  Print(parts);

  parts = (NewStr("::"))->split(sep);
  ASSERT_EQ(3, len(parts));
  ASSERT(str_equals(kEmptyString, parts->index(0)));
  ASSERT(str_equals(kEmptyString, parts->index(1)));
  ASSERT(str_equals(kEmptyString, parts->index(2)));
  Print(parts);

  parts = (NewStr("a:b"))->split(sep);
  ASSERT_EQ(2, len(parts));
  Print(parts);
  ASSERT(str_equals0("a", parts->index(0)));
  ASSERT(str_equals0("b", parts->index(1)));

  parts = (NewStr("abc:def:"))->split(sep);
  ASSERT_EQ(3, len(parts));
  Print(parts);
  ASSERT(str_equals0("abc", parts->index(0)));
  ASSERT(str_equals0("def", parts->index(1)));
  ASSERT(str_equals(kEmptyString, parts->index(2)));

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
  ASSERT(str_equals0("f", kStrFood->index(0)));

  ASSERT(str_equals0("d", kStrFood->index(-1)));

  ASSERT(str_equals0("ood", kStrFood->slice(1)));
  ASSERT(str_equals0("oo", kStrFood->slice(1, 3)));
  ASSERT(str_equals0("oo", kStrFood->slice(1, -1)));
  ASSERT(str_equals0("o", kStrFood->slice(-3, -2)));
  ASSERT(str_equals0("fo", kStrFood->slice(-4, -2)));

  log("strip()");
  ASSERT(str_equals0(" abc", NewStr(" abc ")->rstrip()));
  ASSERT(str_equals0(" def", NewStr(" def")->rstrip()));

  ASSERT(str_equals0("", kEmptyString->rstrip()));
  ASSERT(str_equals0("", kEmptyString->strip()));

  ASSERT(str_equals0("123", NewStr(" 123 ")->strip()));
  ASSERT(str_equals0("123", NewStr(" 123")->strip()));
  ASSERT(str_equals0("123", NewStr("123 ")->strip()));

  Str* input = nullptr;
  Str* arg = nullptr;
  Str* expected = nullptr;
  Str* result = nullptr;
  StackRoots _roots({&input, &arg, &expected, &result});

  log("startswith endswith");

  // arg needs to be separate here because order of evaluation isn't defined!!!
  // CRASHES:
  //   ASSERT(input->startswith(NewStr("ab")));
  // Will this because a problem for mycpp?  I think you have to detect this
  // case:
  //   f(Alloc<Foo>(), new Alloc<Bar>())
  // Allocation can't happen INSIDE an arg list.

  input = NewStr("abc");
  ASSERT(input->startswith(kEmptyString));
  ASSERT(input->endswith(kEmptyString));

  ASSERT(input->startswith(input));
  ASSERT(input->endswith(input));

  arg = NewStr("ab");
  ASSERT(input->startswith(arg));
  ASSERT(!input->endswith(arg));

  arg = NewStr("bc");
  ASSERT(!input->startswith(arg));
  ASSERT(input->endswith(arg));

  log("rjust() and ljust()");
  input = NewStr("13");
  ASSERT(str_equals0("  13", input->rjust(4, kSpace)));
  ASSERT(str_equals0(" 13", input->rjust(3, kSpace)));
  ASSERT(str_equals0("13", input->rjust(2, kSpace)));
  ASSERT(str_equals0("13", input->rjust(1, kSpace)));

  ASSERT(str_equals0("13  ", input->ljust(4, kSpace)));
  ASSERT(str_equals0("13 ", input->ljust(3, kSpace)));
  ASSERT(str_equals0("13", input->ljust(2, kSpace)));
  ASSERT(str_equals0("13", input->ljust(1, kSpace)));

  log("join()");

  List<Str*>* L1 = nullptr;
  List<Str*>* L2 = nullptr;
  List<Str*>* empty_list = nullptr;
  StackRoots _roots2({&L1, &L2, &empty_list});

  L1 = NewList<Str*>(std::initializer_list<Str*>{kStrFood, kStrFoo});

  // Join by empty string
  ASSERT(str_equals0("foodfoo", kEmptyString->join(L1)));

  // Join by NUL
  expected = NewStr("food\0foo", 8);
  arg = NewStr("\0", 1);
  result = arg->join(L1);
  ASSERT(str_equals(expected, result));

  // Singleton list
  L2 = NewList<Str*>(std::initializer_list<Str*>{kStrFoo});
  ASSERT(str_equals0("foo", kEmptyString->join(L2)));

  // Empty list
  empty_list = NewList<Str*>(std::initializer_list<Str*>{});

  result = kEmptyString->join(empty_list);
  ASSERT(str_equals(kEmptyString, result));
  ASSERT_EQ(0, len(result));

  result = kSpace->join(empty_list);
  ASSERT(str_equals(kEmptyString, result));
  ASSERT_EQ(0, len(result));

  PASS();
}

TEST str_funcs_test() {
  log("str_concat()");
  ASSERT(str_equals0("foodfood", str_concat(kStrFood, kStrFood)));
  ASSERT(str_equals(kEmptyString, str_concat(kEmptyString, kEmptyString)));

  log("str_repeat()");

  Str* s = nullptr;
  Str* result = nullptr;
  StackRoots _roots({&s, &result});

  // -1 is allowed by Python and used by Oil!
  s = NewStr("abc");
  ASSERT(str_equals(kEmptyString, str_repeat(s, -1)));
  ASSERT(str_equals(kEmptyString, str_repeat(s, 0)));

  result = str_repeat(s, 1);
  ASSERT(str_equals(s, result));

  result = str_repeat(s, 3);
  ASSERT(str_equals0("abcabcabc", result));

  ASSERT(str_equals0("''", repr(kEmptyString)));
  ASSERT(str_equals0("\"'\"", repr(NewStr("'"))));
  ASSERT(str_equals0("\"'single'\"", repr(NewStr("'single'"))));
  ASSERT(str_equals0("'\"double\"'", repr(NewStr("\"double\""))));

  // this one is truncated
  s = NewStr("NUL \x00 NUL", 9);
  ASSERT(str_equals0("'NUL \\x00 NUL'", repr(s)));

  result = repr(NewStr("tab\tline\nline\r\n"));
  print(result);
  ASSERT(str_equals0("'tab\\tline\\nline\\r\\n'", result));

  result = repr(NewStr("high \xFF \xFE high"));
  ASSERT(str_equals0("'high \\xff \\xfe high'", result));

  s = NewStr("A");
  ASSERT_EQ(65, ord(s));

  result = chr(65);
  ASSERT(str_equals(s, result));

  PASS();
}

TEST str_iters_test() {
  for (StrIter it(kStrFood); !it.Done(); it.Next()) {
    print(it.Value());
  }

  PASS();
}

TEST list_methods_test() {
  auto init = std::initializer_list<int>{5, 6, 7, 8};

  List<int>* ints = nullptr;
  StackRoots _roots({&ints});

  ints = NewList<int>(init);

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

  auto other = NewList<int>(std::initializer_list<int>{-1, -2});
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
  auto ints = NewList<int>(init);

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

  Str *a = nullptr, *aa = nullptr, *b = nullptr;
  StackRoots _roots({&a, &aa, &b});

  a = NewStr("a");
  aa = NewStr("aa");
  b = NewStr("b");

  ASSERT_EQ(0, str_cmp(kEmptyString, kEmptyString));
  ASSERT_EQ(-1, str_cmp(kEmptyString, a));
  ASSERT_EQ(-1, str_cmp(a, aa));
  ASSERT_EQ(-1, str_cmp(a, b));

  ASSERT_EQ(1, str_cmp(b, a));
  ASSERT_EQ(1, str_cmp(b, kEmptyString));

  List<Str*>* strs = nullptr;
  StackRoots _roots2({&strs});
  strs = Alloc<List<Str*>>();

  strs->append(a);
  strs->append(aa);
  strs->append(b);
  strs->append(kEmptyString);
  ASSERT_EQ(4, len(strs));  // ['a', 'aa', 'b', '']

  strs->sort();  // ['', 'a', 'aa', 'b']
  ASSERT_EQ(4, len(strs));
  ASSERT(str_equals(kEmptyString, strs->index(0)));
  ASSERT(str_equals0("a", strs->index(1)));
  ASSERT(str_equals0("aa", strs->index(2)));
  ASSERT(str_equals0("b", strs->index(3)));

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

  Str* s = nullptr;
  Str* nul = nullptr;
  StackRoots _roots({&s, &nul});

  s = NewStr("foo\0 ", 5);
  ASSERT(str_contains(s, kSpace));

  // this ends with a NUL, but also has a NUL terinator.
  nul = NewStr("\0", 1);
  ASSERT(str_contains(s, nul));
  ASSERT(!str_contains(kSpace, nul));

  log("  List<Str*>");
  List<Str*>* strs = nullptr;
  List<int>* ints = nullptr;
  List<double>* floats = nullptr;

  StackRoots _roots2({&strs, &ints, &floats});

  strs = Alloc<List<Str*>>();

  strs->append(kSpace);
  s = NewStr(" ");  // LOCAL space
  ASSERT(list_contains(strs, s));
  ASSERT(!list_contains(strs, kStrFoo));

  strs->append(kStrFoo);
  ASSERT(list_contains(strs, kStrFoo));

  log("  ints");
  ints = NewList<int>(std::initializer_list<int>{1, 2, 3});
  ASSERT(list_contains(ints, 1));

  ASSERT(!list_contains(ints, 42));

  log("  floats");
  floats = NewList<double>(std::initializer_list<double>{0.5, 0.25, 0.0});
  ASSERT(list_contains(floats, 0.0));
  ASSERT(!list_contains(floats, 42.0));

  PASS();
}

TEST dict_methods_test() {
  Dict<int, Str*>* d = nullptr;
  Dict<Str*, int>* d2 = nullptr;
  Str* key = nullptr;
  StackRoots _roots({&d, &d2, &key});

  d = Alloc<Dict<int, Str*>>();
  d->set(1, kStrFoo);
  ASSERT(str_equals0("foo", d->index(1)));

  d2 = Alloc<Dict<Str*, int>>();
  key = NewStr("key");
  d2->set(key, 42);
  ASSERT_EQ(42, d2->index(key));

  PASS();

  d2->set(NewStr("key2"), 2);
  d2->set(NewStr("key3"), 3);

  ASSERT_EQ_FMT(3, len(d2), "%d");

  auto keys = d2->keys();
  ASSERT_EQ_FMT(3, len(keys), "%d");

  // Retain insertion order
  ASSERT(str_equals0("key", keys->index(0)));
  ASSERT(str_equals0("key2", keys->index(1)));
  ASSERT(str_equals0("key3", keys->index(2)));

  mylib::dict_remove(d2, NewStr("key"));
  ASSERT_EQ_FMT(2, len(d2), "%d");

  auto keys2 = d2->keys();
  ASSERT_EQ_FMT(2, len(keys2), "%d");
  ASSERT(str_equals0("key2", keys2->index(0)));
  ASSERT(str_equals0("key3", keys2->index(1)));

  auto values = d2->values();
  ASSERT_EQ_FMT(2, len(values), "%d");
  ASSERT_EQ(2, values->index(0));
  ASSERT_EQ(3, values->index(1));

  int j = 0;
  for (DictIter<Str*, int> it(d2); !it.Done(); it.Next()) {
    auto key = it.Key();
    auto value = it.Value();
    log("d2 key = %s, value = %d", key->data_, value);
    ++j;
  }
  ASSERT_EQ_FMT(len(d2), j, "%d");

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

  auto keys3 = sorted(d3);
  ASSERT_EQ(3, len(keys3));
  ASSERT(str_equals0("a", keys3->index(0)));
  ASSERT(str_equals0("b", keys3->index(1)));
  ASSERT(str_equals0("c", keys3->index(2)));

  auto keys4 = d3->keys();
  ASSERT(list_contains(keys4, a));
  ASSERT(!list_contains(keys4, NewStr("zzz")));

  ASSERT(dict_contains(d3, a));
  mylib::dict_remove(d3, a);
  ASSERT(!dict_contains(d3, a));
  ASSERT_EQ(2, len(d3));

  // Test a different type of dict, to make sure partial template
  // specialization works
  auto ss = Alloc<Dict<Str*, Str*>>();
  ss->set(a, a);
  ASSERT_EQ(1, len(ss));
  ASSERT_EQ(1, len(ss->keys()));
  ASSERT_EQ(1, len(ss->values()));

  int k = 0;
  for (DictIter<Str*, Str*> it(ss); !it.Done(); it.Next()) {
    auto key = it.Key();
    log("ss key = %s", key->data_);
    ++k;
  }
  ASSERT_EQ_FMT(len(ss), k, "%d");

  mylib::dict_remove(ss, a);
  ASSERT_EQ(0, len(ss));

  int m = 0;
  for (DictIter<Str*, Str*> it(ss); !it.Done(); it.Next()) {
    auto key = it.Key();
    log("ss key = %s", key->data_);
    ++m;
  }
  ASSERT_EQ_FMT(0, m, "%d");
  ASSERT_EQ_FMT(len(ss), m, "%d");

  PASS();
}

TEST dict_funcs_test() {
  PASS();
}

TEST dict_iters_test() {
  Dict<Str*, int>* d2 = nullptr;
  List<Str*>* keys = nullptr;
  StackRoots _roots({&d2, &keys});

  d2 = Alloc<Dict<Str*, int>>();
  d2->set(kStrFoo, 2);
  d2->set(kStrBar, 3);

  keys = d2->keys();
  for (int i = 0; i < len(keys); ++i) {
    printf("k %s\n", keys->index(i)->data_);
  }

  log("  iterating over Dict");
  for (DictIter<Str*, int> it(d2); !it.Done(); it.Next()) {
    log("k = %s, v = %d", it.Key()->data_, it.Value());
  }

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(print_test);
  RUN_TEST(formatter_test);

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

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
