#include "mycpp/mylib_old.h"

#include <assert.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>   // vprintf

#include "vendor/greatest.h"

using mylib::StrFromC;

// Emulating the gc_heap API.  COPIED from gc_heap_test.cc
TEST test_str_creation() {
  Str* s = StrFromC("foo");
  ASSERT_EQ(3, len(s));
  ASSERT_EQ(0, strcmp("foo", s->data_));

  // String with internal NUL
  Str* s2 = StrFromC("foo\0bar", 7);
  ASSERT_EQ(7, len(s2));
  ASSERT_EQ(0, memcmp("foo\0bar\0", s2->data_, 8));

  Str* s3 = mylib::AllocStr(1);
  ASSERT_EQ(1, len(s3));
  ASSERT_EQ(0, memcmp("\0\0", s3->data_, 2));

  // Test truncating a string
  //
  // NOTE(Jesse): It's undefined to call `len()` after allocating with this
  // function because it explicitly doesn't set the length!!
  /* Str* s4 = mylib::OverAllocatedStr(7); */

  Str* s4 = mylib::AllocStr(7);
  ASSERT_EQ(7, len(s4));
  ASSERT_EQ(0, memcmp("\0\0\0\0\0\0\0\0", s4->data_, 8));

  // Hm annoying that we have to do a const_cast
  memcpy(s4->data(), "foo", 3);
  strcpy(s4->data(), "foo");
  s4->SetObjLenFromStrLen(3);

  ASSERT_EQ(3, len(s4));
  ASSERT_EQ(0, strcmp("foo", s4->data_));

  PASS();
}

TEST test_str_to_int() {
  int i;
  bool ok;

  ok = _str_to_int(StrFromC("345"), &i, 10);
  ASSERT(ok);
  ASSERT_EQ_FMT(345, i, "%d");

  ok = _str_to_int(StrFromC("1234567890"), &i, 10);
  ASSERT(ok);
  ASSERT(i == 1234567890);

  // overflow
  ok = _str_to_int(StrFromC("12345678901234567890"), &i, 10);
  ASSERT(!ok);

  // underflow
  ok = _str_to_int(StrFromC("-12345678901234567890"), &i, 10);
  ASSERT(!ok);

  // negative
  ok = _str_to_int(StrFromC("-123"), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Leading space is OK!
  ok = _str_to_int(StrFromC(" -123"), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Trailing space is OK!  NOTE: This fails!
  ok = _str_to_int(StrFromC(" -123  "), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Empty string isn't an integer
  ok = _str_to_int(StrFromC(""), &i, 10);
  ASSERT(!ok);

  ok = _str_to_int(StrFromC("xx"), &i, 10);
  ASSERT(!ok);

  // Trailing garbage
  ok = _str_to_int(StrFromC("42a"), &i, 10);
  ASSERT(!ok);

  i = to_int(StrFromC("ff"), 16);
  ASSERT(i == 255);

  // strtol allows 0x prefix
  i = to_int(StrFromC("0xff"), 16);
  ASSERT(i == 255);

  // TODO: test ValueError here
  // i = to_int(StrFromC("0xz"), 16);

  i = to_int(StrFromC("0"), 16);
  ASSERT(i == 0);

  i = to_int(StrFromC("077"), 8);
  ASSERT_EQ_FMT(63, i, "%d");

  bool caught = false;
  try {
    i = to_int(StrFromC("zzz"));
  } catch (ValueError* e) {
    caught = true;
  }
  ASSERT(caught);

  PASS();
}

TEST test_str_funcs() {
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

void Print(List<Str*>* parts) {
  log("---");
  log("len = %d", len(parts));
  for (int i = 0; i < len(parts); ++i) {
    Str* s = parts->index_(i);
    printf("%d [ %s ]\n", i, s->data_);
  }
}

TEST test_list_funcs() {
  std::vector<int> v;
  v.push_back(0);
  log("v.size = %d", v.size());
  v.erase(v.begin());
  log("v.size = %d", v.size());

  log("  ints");
  auto ints = new List<int>({4, 5, 6});
  log("-- before pop(0)");
  for (int i = 0; i < len(ints); ++i) {
    log("ints[%d] = %d", i, ints->index_(i));
  }
  ASSERT_EQ(3, len(ints));  // [4, 5, 6]
  ints->pop(0);             // [5, 6]

  ASSERT_EQ(2, len(ints));
  ASSERT_EQ_FMT(5, ints->index_(0), "%d");
  ASSERT_EQ_FMT(6, ints->index_(1), "%d");

  ints->reverse();
  ASSERT_EQ(2, len(ints));  // [6, 5]

  ASSERT_EQ_FMT(6, ints->index_(0), "%d");
  ASSERT_EQ_FMT(5, ints->index_(1), "%d");

  ints->append(9);  // [6, 5, 9]
  ASSERT_EQ(3, len(ints));

  ints->reverse();  // [9, 5, 6]
  ASSERT_EQ(9, ints->index_(0));
  ASSERT_EQ(5, ints->index_(1));
  ASSERT_EQ(6, ints->index_(2));

  ints->set(0, 42);
  ints->set(1, 43);
  log("-- after mutation");
  for (int i = 0; i < len(ints); ++i) {
    log("ints[%d] = %d", i, ints->index_(i));
  }

  auto L = list_repeat<Str*>(nullptr, 3);
  log("list_repeat length = %d", len(L));

  auto L2 = list_repeat<bool>(true, 3);
  log("list_repeat length = %d", len(L2));
  log("item 0 %d", L2->index_(0));
  log("item 1 %d", L2->index_(1));

  auto strs = new List<Str*>();
  strs->append(StrFromC("c"));
  strs->append(StrFromC("a"));
  strs->append(StrFromC("b"));
  strs->append(kEmptyString);
  ASSERT_EQ(4, len(strs));  // ['c', 'a', 'b', '']

  strs->sort();
  ASSERT_EQ(4, len(strs));  // ['', 'a', 'b', 'c']
  ASSERT(str_equals(kEmptyString, strs->index_(0)));
  ASSERT(str_equals(StrFromC("a"), strs->index_(1)));
  ASSERT(str_equals(StrFromC("b"), strs->index_(2)));
  ASSERT(str_equals(StrFromC("c"), strs->index_(3)));

  auto a = StrFromC("a");
  auto aa = StrFromC("aa");
  auto b = StrFromC("b");

  ASSERT_EQ(0, int_cmp(0, 0));
  ASSERT_EQ(-1, int_cmp(0, 5));
  ASSERT_EQ(1, int_cmp(0, -5));

  ASSERT_EQ(0, str_cmp(kEmptyString, kEmptyString));
  ASSERT_EQ(-1, str_cmp(kEmptyString, a));
  ASSERT_EQ(-1, str_cmp(a, aa));
  ASSERT_EQ(-1, str_cmp(a, b));

  ASSERT_EQ(1, str_cmp(b, a));
  ASSERT_EQ(1, str_cmp(b, kEmptyString));

  PASS();
}

void ListFunc(std::initializer_list<Str*> init) {
  log("init.size() = %d", init.size());
}

TEST test_list_iters() {
  log("  forward iteration over list");
  auto ints = new List<int>({1, 2, 3});
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
  auto strs = {StrFromC("foo"), StrFromC("bar")};
  ListFunc(strs);

  PASS();
}

TEST test_contains() {
  bool b;

  log("  Str");

  // Degenerate cases
  b = str_contains(StrFromC(""), StrFromC(""));
  ASSERT(b == true);
  b = str_contains(StrFromC("foo"), StrFromC(""));
  ASSERT(b == true);

  // Short circuit
  b = str_contains(StrFromC("foo"), StrFromC("too long"));
  ASSERT(b == false);

  b = str_contains(StrFromC("foo"), StrFromC("oo"));
  ASSERT(b == true);

  b = str_contains(StrFromC("foo"), StrFromC("ood"));
  ASSERT(b == false);

  b = str_contains(StrFromC("foo\0a", 5), StrFromC("a"));
  ASSERT(b == true);

  b = str_contains(StrFromC("foo\0ab", 6), StrFromC("ab"));
  ASSERT(b == true);

  // this ends with a NUL, but also has a NUL terinator.
  Str* s = StrFromC("foo\0", 4);
  b = str_contains(s, StrFromC("\0", 1));
  ASSERT(b == true);

  log("  List<Str*>");
  auto strs = new List<Str*>();
  strs->append(StrFromC("bar"));

  b = list_contains(strs, StrFromC("foo"));
  ASSERT(b == false);

  strs->append(StrFromC("foo"));
  b = list_contains(strs, StrFromC("foo"));
  ASSERT(b == true);

  log("  ints");
  auto ints = new List<int>({1, 2, 3});
  b = list_contains(ints, 1);
  ASSERT(b == true);

  b = list_contains(ints, 42);
  ASSERT(b == false);

  log("  floats");
  auto floats = new List<double>({0.5, 0.25, 0.0});
  b = list_contains(floats, 0.0);
  log("b = %d", b);
  b = list_contains(floats, 42.0);
  log("b = %d", b);

  PASS();
}

TEST test_dict() {
  // TODO: How to initialize constants?

  // Dict d {{"key", 1}, {"val", 2}};
  Dict<int, Str*>* d = new Dict<int, Str*>();
  d->set(1, StrFromC("foo"));
  log("d[1] = %s", d->index_(1)->data_);

  auto d2 = new Dict<Str*, int>();
  Str* key = StrFromC("key");
  d2->set(key, 42);

  log("d2['key'] = %d", d2->index_(key));
  d2->set(StrFromC("key2"), 2);
  d2->set(StrFromC("key3"), 3);

  ASSERT_EQ_FMT(3, len(d2), "%d");
  ASSERT_EQ_FMT(3, len(d2->keys()), "%d");
  ASSERT_EQ_FMT(3, len(d2->values()), "%d");

  d2->clear();
  ASSERT_EQ(0, len(d2));

  log("  iterating over Dict");
  for (DictIter<Str*, int> it(d2); !it.Done(); it.Next()) {
    log("k = %s, v = %d", it.Key()->data_, it.Value());
  }

  Str* v1 = d->get(1);
  log("v1 = %s", v1->data_);
  ASSERT(dict_contains(d, 1));
  ASSERT(!dict_contains(d, 2));

  Str* v2 = d->get(423);  // nonexistent
  log("v2 = %p", v2);

  auto d3 = new Dict<Str*, int>();
  auto a = StrFromC("a");

  d3->set(StrFromC("b"), 11);
  d3->set(StrFromC("c"), 12);
  d3->set(StrFromC("a"), 10);
  ASSERT_EQ(10, d3->index_(StrFromC("a")));
  ASSERT_EQ(11, d3->index_(StrFromC("b")));
  ASSERT_EQ(12, d3->index_(StrFromC("c")));
  ASSERT_EQ(3, len(d3));

  auto keys = sorted(d3);
  ASSERT(str_equals0("a", keys->index_(0)));
  ASSERT(str_equals0("b", keys->index_(1)));
  ASSERT(str_equals0("c", keys->index_(2)));
  ASSERT_EQ(3, len(keys));

  auto keys3 = d3->keys();
  ASSERT(list_contains(keys3, a));
  ASSERT(!list_contains(keys3, StrFromC("zzz")));

  ASSERT(dict_contains(d3, a));
  mylib::dict_remove(d3, a);
  ASSERT(!dict_contains(d3, a));
  ASSERT_EQ(2, len(d3));

  // Test removed item
  for (DictIter<Str*, int> it(d3); !it.Done(); it.Next()) {
    auto key = it.Key();
    printf("d3 key = ");
    print(key);
  }

  // Use the method version
  d3->remove(StrFromC("b"));
  ASSERT(!dict_contains(d3, StrFromC("b")));
  ASSERT_EQ(1, len(d3));

  // Test a different type of dict, to make sure partial template
  // specialization works
  auto ss = new Dict<Str*, Str*>();
  ss->set(a, a);
  ASSERT_EQ(1, len(ss));

  ASSERT_EQ(1, len(ss->keys()));
  ASSERT_EQ(1, len(ss->values()));

  ss->remove(a);
  ASSERT_EQ(0, len(ss));

  // Test removed item
  for (DictIter<Str*, Str*> it(ss); !it.Done(); it.Next()) {
    auto key = it.Key();
    printf("ss key = ");
    print(key);
  }

  // Testing NewDict() stub for ordered dicts ... hm.
  //
  // Dict<int, int>* frame = nullptr;
  // frame = NewDict<int, int>();

  PASS();
}

TEST test_list_tuple() {
  List<int>* L = new List<int>{1, 2, 3};

  log("size: %d", len(L));
  log("");

  Tuple2<int, int>* t2 = new Tuple2<int, int>(5, 6);
  log("t2[0] = %d", t2->at0());
  log("t2[1] = %d", t2->at1());

  Tuple2<int, Str*>* u2 = new Tuple2<int, Str*>(42, StrFromC("hello"));
  log("u2[0] = %d", u2->at0());
  log("u2[1] = %s", u2->at1()->data_);

  log("");

  auto t3 = new Tuple3<int, Str*, Str*>(42, StrFromC("hello"), StrFromC("bye"));
  log("t3[0] = %d", t3->at0());
  log("t3[1] = %s", t3->at1()->data_);
  log("t3[2] = %s", t3->at2()->data_);

  log("");

  auto t4 =
      new Tuple4<int, Str*, Str*, int>(42, StrFromC("4"), StrFromC("four"), -42);

  log("t4[0] = %d", t4->at0());
  log("t4[1] = %s", t4->at1()->data_);
  log("t4[2] = %s", t4->at2()->data_);
  log("t4[3] = %d", t4->at3());

  PASS();
}

TEST test_sizeof() {
  // Str = 16 and List = 24.
  // Rejected ideas about slicing:
  //
  // - Use data[len] == '\0' as OWNING and data[len] != '\0' as a slice?
  //   It doesn't work because s[1:] would always have that problem
  //
  // - s->data == (void*)(s + 1)
  //   Owning string has the data RIGHT AFTER?
  //   Maybe works? but probably a bad idea because of GLOBAL Str instances.

  log("");
  log("sizeof(Str) = %zu", sizeof(Str));
  log("sizeof(List<int>) = %zu", sizeof(List<int>));
  log("sizeof(Dict<int, Str*>) = %zu", sizeof(Dict<int, Str*>));
  log("sizeof(Tuple2<int, int>) = %zu", sizeof(Tuple2<int, int>));
  log("sizeof(Tuple2<Str*, Str*>) = %zu", sizeof(Tuple2<Str*, Str*>));
  log("sizeof(Tuple3<int, int, int>) = %zu", sizeof(Tuple3<int, int, int>));

  PASS();
}

#define PRINT_STRING(str) printf("(%.*s)\n", len(str), (str)->data_)

#define PRINT_LIST(list)                                         \
  for (ListIter<Str*> iter((list)); !iter.Done(); iter.Next()) { \
    Str* piece = iter.Value();                                   \
    printf("(%.*s) ", len(piece), piece->data_);                \
  }                                                              \
  printf("\n")

TEST test_str_replace() {
  printf("\n");

  Str* s0 = StrFromC("ab cd ab ef");

  printf("----- Str::replace -------\n");

  {
    Str* s1 = s0->replace(StrFromC("ab"), StrFromC("--"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("-- cd -- ef")));
  }

  {
    Str* s1 = s0->replace(StrFromC("ab"), StrFromC("----"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("---- cd ---- ef")));
  }

  {
    Str* s1 = s0->replace(StrFromC("ab cd ab ef"), StrFromC("0"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("0")));
  }

  {
    Str* s1 = s0->replace(s0, StrFromC("0"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("0")));
  }

  {
    Str* s1 = s0->replace(StrFromC("no-match"), StrFromC("0"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("ab cd ab ef")));
  }

  {
    Str* s1 = s0->replace(StrFromC("ef"), StrFromC("0"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("ab cd ab 0")));
  }

  {
    Str* s1 = s0->replace(StrFromC("f"), StrFromC("0"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("ab cd ab e0")));
  }

  {
    s0 = StrFromC("ab ab ab");
    Str* s1 = s0->replace(StrFromC("ab"), StrFromC("0"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("0 0 0")));
  }

  {
    s0 = StrFromC("ababab");
    Str* s1 = s0->replace(StrFromC("ab"), StrFromC("0"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("000")));
  }

  {
    s0 = StrFromC("abababab");
    Str* s1 = s0->replace(StrFromC("ab"), StrFromC("0"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("0000")));
  }

  {
    s0 = StrFromC("abc 123");
    Str* s1 = s0->replace(StrFromC("abc"), StrFromC(""));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC(" 123")));
  }

  {
    s0 = StrFromC("abc 123");
    Str* s1 = s0->replace(StrFromC("abc"), StrFromC(""));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC(" 123")));
  }

  {
    s0 = StrFromC("abc 123");
    Str* s1 = s0->replace(StrFromC("abc"), StrFromC("abc"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("abc 123")));
  }

  {
    s0 = StrFromC("aaaa");
    Str* s1 = s0->replace(StrFromC("aa"), StrFromC("bb"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("bbbb")));
  }

  {
    s0 = StrFromC("aaaaaa");
    Str* s1 = s0->replace(StrFromC("aa"), StrFromC("bb"));
    PRINT_STRING(s1);
    ASSERT(str_equals(s1, StrFromC("bbbbbb")));
  }

  // Test NUL replacement
  {
    Str* s_null = StrFromC("abc\0bcd", 7);
    ASSERT_EQ(7, len(s_null));

    Str* re1 = s_null->replace(StrFromC("ab"), StrFromC("--"));
    ASSERT_EQ_FMT(7, len(re1), "%d");
    ASSERT(str_equals(StrFromC("--c\0bcd", 7), re1));

    Str* re2 = s_null->replace(StrFromC("bc"), StrFromC("--"));
    ASSERT_EQ_FMT(7, len(re2), "%d");
    ASSERT(str_equals(StrFromC("a--\0--d", 7), re2));

    Str* re3 = s_null->replace(StrFromC("\0", 1), StrFromC("__"));
    ASSERT_EQ_FMT(8, len(re3), "%d");
    ASSERT(str_equals(StrFromC("abc__bcd", 8), re3));
  }

  PASS();
}

TEST test_str_slice() {
  printf("\n");

  Str* s0 = StrFromC("abcdef");

  printf("------- Str::slice -------\n");

  {  // Happy path
    Str* s1 = s0->slice(0, 5);
    ASSERT(str_equals(s1, StrFromC("abcde")));
    PRINT_STRING(s1);
  }
  {
    Str* s1 = s0->slice(1, 5);
    ASSERT(str_equals(s1, StrFromC("bcde")));
    PRINT_STRING(s1);
  }
  {
    Str* s1 = s0->slice(0, 0);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }
  {
    Str* s1 = s0->slice(0, 6);
    ASSERT(str_equals(s1, StrFromC("abcdef")));
    PRINT_STRING(s1);
  }
  {
    Str* s1 = s0->slice(-6, 6);
    ASSERT(str_equals(s1, StrFromC("abcdef")));
    PRINT_STRING(s1);
  }
  {
    Str* s1 = s0->slice(0, -6);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }
  {
    Str* s1 = s0->slice(-6, -6);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(5, 6);
    ASSERT(str_equals(s1, StrFromC("f")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(6, 6);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(0, -7);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(-7, -7);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(-7, 0);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(6, 6);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(7, 7);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(6, 5);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(7, 5);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(7, 6);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  {
    Str* s1 = s0->slice(7, 7);
    ASSERT(str_equals(s1, StrFromC("")));
    PRINT_STRING(s1);
  }

  printf("---------- Done ----------\n");

  //  NOTE(Jesse): testing all permutations of boundary conditions for
  //  assertions
  int max_len = (len(s0) + 2);
  int min_len = -max_len;

  for (int outer = min_len; outer <= max_len; ++outer) {
    for (int inner = min_len; inner <= max_len; ++inner) {
      s0->slice(outer, inner);
    }
  }

  PASS();
}

TEST test_str_split() {
  printf("\n");

  Str* s0 = StrFromC("abc def");

  printf("------- Str::split -------\n");

  {
    List<Str*>* split_result = s0->split(StrFromC(" "));
    PRINT_LIST(split_result);
    ASSERT(len(split_result) == 2);
    ASSERT(are_equal(split_result->index_(0), StrFromC("abc")));
    ASSERT(are_equal(split_result->index_(1), StrFromC("def")));
  }

  {
    List<Str*>* split_result = (StrFromC("###"))->split(StrFromC("#"));
    PRINT_LIST(split_result);
    ASSERT(len(split_result) == 4);
    ASSERT(are_equal(split_result->index_(0), StrFromC("")));
    ASSERT(are_equal(split_result->index_(1), StrFromC("")));
    ASSERT(are_equal(split_result->index_(2), StrFromC("")));
    ASSERT(are_equal(split_result->index_(3), StrFromC("")));
  }

  {
    List<Str*>* split_result = (StrFromC(" ### "))->split(StrFromC("#"));
    PRINT_LIST(split_result);
    ASSERT(len(split_result) == 4);
    ASSERT(are_equal(split_result->index_(0), StrFromC(" ")));
    ASSERT(are_equal(split_result->index_(1), StrFromC("")));
    ASSERT(are_equal(split_result->index_(2), StrFromC("")));
    ASSERT(are_equal(split_result->index_(3), StrFromC(" ")));
  }

  {
    List<Str*>* split_result = (StrFromC(" # "))->split(StrFromC(" "));
    PRINT_LIST(split_result);
    ASSERT(len(split_result) == 3);
    ASSERT(are_equal(split_result->index_(0), StrFromC("")));
    ASSERT(are_equal(split_result->index_(1), StrFromC("#")));
    ASSERT(are_equal(split_result->index_(2), StrFromC("")));
  }

  {
    List<Str*>* split_result = (StrFromC("  #"))->split(StrFromC("#"));
    PRINT_LIST(split_result);
    ASSERT(len(split_result) == 2);
    ASSERT(are_equal(split_result->index_(0), StrFromC("  ")));
    ASSERT(are_equal(split_result->index_(1), StrFromC("")));
  }

  {
    List<Str*>* split_result = (StrFromC("#  #"))->split(StrFromC("#"));
    PRINT_LIST(split_result);
    ASSERT(len(split_result) == 3);
    ASSERT(are_equal(split_result->index_(0), StrFromC("")));
    ASSERT(are_equal(split_result->index_(1), StrFromC("  ")));
    ASSERT(are_equal(split_result->index_(2), StrFromC("")));
  }

  {
    List<Str*>* split_result = (StrFromC(""))->split(StrFromC(" "));
    PRINT_LIST(split_result);
    ASSERT(len(split_result) == 1);
    ASSERT(are_equal(split_result->index_(0), StrFromC("")));
  }

  // NOTE(Jesse): Failure case.  Not sure if we care about supporting this.
  // It might happen if we do something like : 'weahtevr'.split()
  // Would need to check on what the Python interpreter does in that case to
  // decipher what we'd expect to see.
  //
  /* { */
  /*   List<Str*> *split_result = (StrFromC("weahtevr"))->split(0); */
  /*   PRINT_LIST(split_result); */
  /*   ASSERT(len(split_result) == 1); */
  /*   ASSERT(are_equal(split_result->index_(0), StrFromC(""))); */
  /* } */

  printf("---------- Done ----------\n");

  PASS();
}

TEST test_str_join() {
  printf("\n");

  printf("-------- Str::join -------\n");

  {
    Str* result =
        (StrFromC(""))->join(new List<Str*>({StrFromC("abc"), StrFromC("def")}));
    PRINT_STRING(result);
    ASSERT(are_equal(result, StrFromC("abcdef")));
  }
  {
    Str* result = (StrFromC(" "))
                      ->join(new List<Str*>({StrFromC("abc"), StrFromC("def"),
                                             StrFromC("abc"), StrFromC("def"),
                                             StrFromC("abc"), StrFromC("def"),
                                             StrFromC("abc"), StrFromC("def")}));
    PRINT_STRING(result);
    ASSERT(are_equal(result, StrFromC("abc def abc def abc def abc def")));
  }

  printf("---------- Done ----------\n");

  PASS();
}

TEST test_str_helpers() {
  printf("------ Str::helpers ------\n");

  ASSERT((StrFromC(""))->startswith(StrFromC("")) == true);
  ASSERT((StrFromC(" "))->startswith(StrFromC("")) == true);
  ASSERT((StrFromC(" "))->startswith(StrFromC(" ")) == true);

  ASSERT((StrFromC("  "))->startswith(StrFromC(" ")) == true);

  printf("---------- Done ----------\n");

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  GREATEST_MAIN_BEGIN();

  RUN_TEST(test_str_creation);

  RUN_TEST(test_str_to_int);
  RUN_TEST(test_str_funcs);

  RUN_TEST(test_list_funcs);
  RUN_TEST(test_list_iters);
  RUN_TEST(test_dict);

  RUN_TEST(test_contains);
  RUN_TEST(test_sizeof);

  RUN_TEST(test_list_tuple);

  RUN_TEST(test_str_slice);
  RUN_TEST(test_str_replace);
  RUN_TEST(test_str_split);
  RUN_TEST(test_str_join);

  RUN_TEST(test_str_helpers);

  GREATEST_MAIN_END();
  return 0;
}
