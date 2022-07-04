#include "mycpp/mylib_leaky.h"

#include <assert.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>   // vprintf

#include "vendor/greatest.h"

// Emulating the gc_heap API.  COPIED from gc_heap_test.cc
TEST test_str_creation() {
  Str* s = mylib::CopyStr("foo");
  ASSERT_EQ(3, len(s));
  ASSERT_EQ(0, strcmp("foo", s->data_));

  // String with internal NUL
  Str* s2 = mylib::CopyStr("foo\0bar", 7);
  ASSERT_EQ(7, len(s2));
  ASSERT_EQ(0, memcmp("foo\0bar\0", s2->data_, 8));

  Str* s3 = mylib::AllocStr(1);
  ASSERT_EQ(1, len(s3));
  ASSERT_EQ(0, memcmp("\0\0", s3->data_, 2));

  // Test truncating a string
  Str* s4 = mylib::OverAllocatedStr(7);
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

// TODO: Could use ASSERT_EQ_T to customize equality and print difference.
//
// Example:
//
// https://github.com/silentbicycle/greatest/blob/master/example.c#L71

TEST test_str0() {
  Str* s = new Str("foo");
  ASSERT_EQ(3, len(s));

  // we can get the last one
  ASSERT('\0' == s->data_[3]);

  // ASAN ERROR!  Yes.
  // ASSERT('\0' == s->data_[4]);

  Str* space = new Str("foo ");
  ASSERT_EQ(4, len(space));

  ASSERT_EQ_FMT(3, len(space->strip()), "%d");

  // WRONG WAY TO DO IT.  We get 4 instead of 3.
  int bad_len = strlen(space->strip()->data_);
  log("bad_len = %d", bad_len);

  mylib::Str0 space0(space->strip());
  int good_len = strlen(space0.Get());

  ASSERT_EQ_FMT(3, good_len, "%d");

  PASS();
}

TEST test_str_to_int() {
  int i;
  bool ok;

  ok = _str_to_int(new Str("345"), &i, 10);
  ASSERT(ok);
  ASSERT_EQ_FMT(345, i, "%d");

  // Hack to test slicing.  Truncated "345" at "34".
  ok = _str_to_int(new Str("345", 2), &i, 10);
  ASSERT(ok);
  ASSERT_EQ_FMT(34, i, "%d");

  ok = _str_to_int(new Str("1234567890"), &i, 10);
  ASSERT(ok);
  ASSERT(i == 1234567890);

  // overflow
  ok = _str_to_int(new Str("12345678901234567890"), &i, 10);
  ASSERT(!ok);

  // underflow
  ok = _str_to_int(new Str("-12345678901234567890"), &i, 10);
  ASSERT(!ok);

  // negative
  ok = _str_to_int(new Str("-123"), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Leading space is OK!
  ok = _str_to_int(new Str(" -123"), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Trailing space is OK!  NOTE: This fails!
  ok = _str_to_int(new Str(" -123  "), &i, 10);
  ASSERT(ok);
  ASSERT(i == -123);

  // Empty string isn't an integer
  ok = _str_to_int(new Str(""), &i, 10);
  ASSERT(!ok);

  ok = _str_to_int(new Str("xx"), &i, 10);
  ASSERT(!ok);

  // Trailing garbage
  ok = _str_to_int(new Str("42a"), &i, 10);
  ASSERT(!ok);

  i = to_int(new Str("ff"), 16);
  ASSERT(i == 255);

  // strtol allows 0x prefix
  i = to_int(new Str("0xff"), 16);
  ASSERT(i == 255);

  // TODO: test ValueError here
  // i = to_int(new Str("0xz"), 16);

  i = to_int(new Str("0"), 16);
  ASSERT(i == 0);

  i = to_int(new Str("077"), 8);
  ASSERT_EQ_FMT(63, i, "%d");

  bool caught = false;
  try {
    i = to_int(new Str("zzz"));
  } catch (ValueError* e) {
    caught = true;
  }
  ASSERT(caught);

  PASS();
}

TEST test_str_funcs() {
  Str* int_str;

  int int_min = -(1 << 31);

  int_str = mylib::hex_lower(15);
  ASSERT(str_equals0("f", int_str));
  print(mylib::hex_lower(int_min));  // ASAN implicitly checks this

  int_str = mylib::hex_upper(15);
  ASSERT(str_equals0("F", int_str));
  print(mylib::hex_upper(int_min));  // ASAN

  int_str = mylib::octal(15);
  ASSERT(str_equals0("17", int_str));
  print(mylib::octal(int_min));  // ASAN

  Str* s1 = new Str("abc\0bcd", 7);
  ASSERT_EQ(7, len(s1));

  // Str* re1 = s1->replace(new Str("ab"), new Str("--"));
  // cstring-BUG!
  // ASSERT_EQ_FMT(7, len(re1), "%d");
  // ASSERT(str_equals(new Str("--c\0bcd", 7), re1));

  // Str* re2 = s1->replace(new Str("bc"), new Str("--"));
  // ASSERT(str_equals(new Str("a--\0--d", 7), re1));

  log("split_once()");
  Tuple2<Str*, Str*> t = mylib::split_once(new Str("foo=bar"), new Str("="));
  ASSERT(str_equals(t.at0(), new Str("foo")));
  ASSERT(str_equals(t.at1(), new Str("bar")));

  Tuple2<Str*, Str*> u = mylib::split_once(new Str("foo="), new Str("="));
  ASSERT(str_equals(u.at0(), new Str("foo")));
  ASSERT(str_equals(u.at1(), new Str("")));

  Tuple2<Str*, Str*> v = mylib::split_once(new Str("foo="), new Str("Z"));
  ASSERT(str_equals(v.at0(), new Str("foo=")));
  ASSERT(v.at1() == nullptr);

  Tuple2<Str*, Str*> w = mylib::split_once(new Str(""), new Str("Z"));
  ASSERT(str_equals(w.at0(), new Str("")));
  ASSERT(w.at1() == nullptr);

  PASS();
}

void Print(List<Str*>* parts) {
  log("---");
  log("len = %d", len(parts));
  for (int i = 0; i < len(parts); ++i) {
    mylib::Str0 s0(parts->index_(i));
    printf("%d [", i);
    fputs(s0.Get(), stdout);
    fputs("]\n", stdout);
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
  strs->append(new Str("c"));
  strs->append(new Str("a"));
  strs->append(new Str("b"));
  strs->append(kEmptyString);
  ASSERT_EQ(4, len(strs));  // ['c', 'a', 'b', '']

  strs->sort();
  ASSERT_EQ(4, len(strs));  // ['', 'a', 'b', 'c']
  ASSERT(str_equals(kEmptyString, strs->index_(0)));
  ASSERT(str_equals(new Str("a"), strs->index_(1)));
  ASSERT(str_equals(new Str("b"), strs->index_(2)));
  ASSERT(str_equals(new Str("c"), strs->index_(3)));

  auto a = new Str("a");
  auto aa = new Str("aa");
  auto b = new Str("b");

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
  auto strs = {new Str("foo"), new Str("bar")};
  ListFunc(strs);

  PASS();
}

TEST test_contains() {
  bool b;

  log("  Str");
  b = str_contains(new Str("foo"), new Str("oo"));
  ASSERT(b == true);

  b = str_contains(new Str("foo"), new Str("ood"));
  ASSERT(b == false);

  // cstring-BUG
  b = str_contains(new Str("foo\0a", 5), new Str("a"));
  // ASSERT(b == true);

  // this ends with a NUL, but also has a NUL terinator.
  Str* s = new Str("foo\0", 4);
  b = str_contains(s, new Str("\0", 1));
  ASSERT(b == true);

  log("  List<Str*>");
  auto strs = new List<Str*>();
  strs->append(new Str("bar"));

  b = list_contains(strs, new Str("foo"));
  ASSERT(b == false);

  strs->append(new Str("foo"));
  b = list_contains(strs, new Str("foo"));
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
  d->set(1, new Str("foo"));
  log("d[1] = %s", d->index_(1)->data_);

  auto d2 = new Dict<Str*, int>();
  Str* key = new Str("key");
  d2->set(key, 42);

  log("d2['key'] = %d", d2->index_(key));
  d2->set(new Str("key2"), 2);
  d2->set(new Str("key3"), 3);

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
  auto a = new Str("a");

  d3->set(new Str("b"), 11);
  d3->set(new Str("c"), 12);
  d3->set(new Str("a"), 10);
  ASSERT_EQ(10, d3->index_(new Str("a")));
  ASSERT_EQ(11, d3->index_(new Str("b")));
  ASSERT_EQ(12, d3->index_(new Str("c")));
  ASSERT_EQ(3, len(d3));

  auto keys = sorted(d3);
  ASSERT(str_equals0("a", keys->index_(0)));
  ASSERT(str_equals0("b", keys->index_(1)));
  ASSERT(str_equals0("c", keys->index_(2)));
  ASSERT_EQ(3, len(keys));

  auto keys3 = d3->keys();
  ASSERT(list_contains(keys3, a));
  ASSERT(!list_contains(keys3, new Str("zzz")));

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
  d3->remove(new Str("b"));
  ASSERT(!dict_contains(d3, new Str("b")));
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
    log("ss key = ");
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

  Tuple2<int, Str*>* u2 = new Tuple2<int, Str*>(42, new Str("hello"));
  log("u2[0] = %d", u2->at0());
  log("u2[1] = %s", u2->at1()->data_);

  log("");

  auto t3 = new Tuple3<int, Str*, Str*>(42, new Str("hello"), new Str("bye"));
  log("t3[0] = %d", t3->at0());
  log("t3[1] = %s", t3->at1()->data_);
  log("t3[2] = %s", t3->at2()->data_);

  log("");

  auto t4 =
      new Tuple4<int, Str*, Str*, int>(42, new Str("4"), new Str("four"), -42);

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

TEST test_str_slice() {
  printf("\n");

  Str* s0 = new Str("abcdef");

  printf("------- Happy Path -------\n");

  { // Happy path
    Str* s1 = s0->slice(0, 5);
    ASSERT(str_equals(s1, new Str("abcde")));
    printf("%s\n", s1->data());
  }
  {
    Str* s1 = s0->slice(1, 5);
    ASSERT(str_equals(s1, new Str("bcde")));
    printf("%s\n", s1->data());
  }
  {
    Str* s1 = s0->slice(0, 0);
    ASSERT(str_equals(s1, new Str("")));
    printf("%s\n", s1->data());
  }
  {
    Str* s1 = s0->slice(0, 6);
    ASSERT(str_equals(s1, new Str("abcdef")));
    printf("%s\n", s1->data());
  }
  {
    Str* s1 = s0->slice(-6, 6);
    ASSERT(str_equals(s1, new Str("abcdef")));
    printf("%s\n", s1->data());
  }
  {
    Str* s1 = s0->slice(0, -6);
    ASSERT(str_equals(s1, new Str("")));
    printf("%s\n", s1->data());
  }
  {
    Str* s1 = s0->slice(-6, -6);
    ASSERT(str_equals(s1, new Str("")));
    printf("%s\n", s1->data());
  }

  {
    Str* s1 = s0->slice(5, 6);
    ASSERT(str_equals(s1, new Str("f")));
    printf("%s\n", s1->data());
  }

  {
    Str* s1 = s0->slice(6, 6);
    ASSERT(str_equals(s1, new Str("")));
    printf("%s\n", s1->data());
  }


  printf("---- Infinite Sadness ----\n");

  {
    Str* s1 = s0->slice(0, -7);
    ASSERT(str_equals(s1, new Str("")));
    printf("%s\n", s1->data());
  }

  {
    Str* s1 = s0->slice(-7, -7);
    ASSERT(str_equals(s1, new Str("")));
    printf("%s\n", s1->data());
  }

  {
    Str* s1 = s0->slice(-7, 0);
    ASSERT(str_equals(s1, new Str("")));
    printf("%s\n", s1->data());
  }

  {
    Str* s1 = s0->slice(6, 6);
    ASSERT(str_equals(s1, new Str("")));
    printf("%s\n", s1->data());
  }

  {
    Str* s1 = s0->slice(7, 7);
    ASSERT(str_equals(s1, new Str("")));
    printf("%s\n", s1->data());
  }

  {
    Str* s1 = s0->slice(6, 5);
    ASSERT(str_equals(s1, new Str("")));
    printf("%s\n", s1->data());
  }

  {
    Str* s1 = s0->slice(7, 5);
    ASSERT(str_equals(s1, new Str("")));
    printf("%s\n", s1->data());
  }

  {
    Str* s1 = s0->slice(7, 6);
    ASSERT(str_equals(s1, new Str("")));
    printf("%s\n", s1->data());
  }

  {
    Str* s1 = s0->slice(7, 7);
    ASSERT(str_equals(s1, new Str("")));
    printf("%s\n", s1->data());
  }

  printf("---------- Done ----------\n");

  //  NOTE(Jesse): testing all permutations of boundary conditions for assertions
  int max_len = (s0->len_ +2);
  int min_len = -max_len;

  for (int outer = min_len; outer <= max_len; ++outer)
  {
    for (int inner = min_len; inner <= max_len; ++inner)
    {
      s0->slice(outer, inner);
    }
  }


  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  GREATEST_MAIN_BEGIN();

  RUN_TEST(test_str_creation);

  RUN_TEST(test_str0);
  RUN_TEST(test_str_to_int);
  RUN_TEST(test_str_funcs);

  RUN_TEST(test_list_funcs);
  RUN_TEST(test_list_iters);
  RUN_TEST(test_dict);

  RUN_TEST(test_contains);
  RUN_TEST(test_sizeof);

  RUN_TEST(test_list_tuple);

  RUN_TEST(test_str_slice);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
