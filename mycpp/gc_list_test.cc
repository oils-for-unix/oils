#include <assert.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>   // vprintf

#include "mycpp/runtime.h"
#include "vendor/greatest.h"

void Print(List<Str*>* parts) {
  log("---");
  log("len = %d", len(parts));
  for (int i = 0; i < len(parts); ++i) {
    Str* s = parts->index_(i);
    printf("%d [ %s ]\n", i, s->data_);
  }
}

// TODO:
//
// - Test what happens append() runs over the max heap size
//   - how does it trigger a collection?

TEST test_list_gc_header() {
  auto list1 = NewList<int>();
  StackRoots _roots1({&list1});
  auto list2 = NewList<Str*>();
  StackRoots _roots2({&list2});

  ASSERT_EQ(0, len(list1));
  ASSERT_EQ(0, len(list2));

  ASSERT_EQ_FMT(0, list1->capacity_, "%d");
  ASSERT_EQ_FMT(0, list2->capacity_, "%d");

  ASSERT_EQ_FMT(Tag::FixedSize, list1->header_.heap_tag_, "%d");
  ASSERT_EQ_FMT(Tag::FixedSize, list2->header_.heap_tag_, "%d");

  // 8 byte obj header + 2 integers + pointer
  ASSERT_EQ_FMT(24, list1->header_.obj_len_, "%d");
  ASSERT_EQ_FMT(24, list2->header_.obj_len_, "%d");

  // Make sure they're on the heap
#ifndef MARK_SWEEP
  int diff1 = reinterpret_cast<char*>(list1) - gHeap.from_space_.begin_;
  int diff2 = reinterpret_cast<char*>(list2) - gHeap.from_space_.begin_;
  ASSERT(diff1 < 1024);
  ASSERT(diff2 < 1024);
#endif

  auto more = NewList<int>(std::initializer_list<int>{11, 22, 33});
  StackRoots _roots3({&more});
  list1->extend(more);
  ASSERT_EQ_FMT(3, len(list1), "%d");

  // 32 byte block - 8 byte header = 24 bytes, 6 elements
  ASSERT_EQ_FMT(6, list1->capacity_, "%d");
  ASSERT_EQ_FMT(Tag::Opaque, list1->slab_->heap_tag_, "%d");

  // 8 byte header + 3*4 == 8 + 12 == 20, rounded up to power of 2
  ASSERT_EQ_FMT(32, list1->slab_->obj_len_, "%d");

  ASSERT_EQ_FMT(11, list1->index_(0), "%d");
  ASSERT_EQ_FMT(22, list1->index_(1), "%d");
  ASSERT_EQ_FMT(33, list1->index_(2), "%d");

  log("extending");
  auto more2 = NewList<int>(std::initializer_list<int>{44, 55, 66, 77});
  StackRoots _roots4({&more2});
  list1->extend(more2);

  // 64 byte block - 8 byte header = 56 bytes, 14 elements
  ASSERT_EQ_FMT(14, list1->capacity_, "%d");
  ASSERT_EQ_FMT(7, len(list1), "%d");

  // 8 bytes header + 7*4 == 8 + 28 == 36, rounded up to power of 2
  ASSERT_EQ_FMT(64, list1->slab_->obj_len_, "%d");

  ASSERT_EQ_FMT(11, list1->index_(0), "%d");
  ASSERT_EQ_FMT(22, list1->index_(1), "%d");
  ASSERT_EQ_FMT(33, list1->index_(2), "%d");
  ASSERT_EQ_FMT(44, list1->index_(3), "%d");
  ASSERT_EQ_FMT(55, list1->index_(4), "%d");
  ASSERT_EQ_FMT(66, list1->index_(5), "%d");
  ASSERT_EQ_FMT(77, list1->index_(6), "%d");

  list1->append(88);
  ASSERT_EQ_FMT(88, list1->index_(7), "%d");
  ASSERT_EQ_FMT(8, len(list1), "%d");

#ifndef MARK_SWEEP
  int d_slab = reinterpret_cast<char*>(list1->slab_) - gHeap.from_space_.begin_;
  ASSERT(d_slab < 1024);
#endif

  log("list1_ = %p", list1);
  log("list1->slab_ = %p", list1->slab_);

  auto str1 = StrFromC("foo");
  StackRoots _roots5({&str1});
  log("str1 = %p", str1);
  auto str2 = StrFromC("bar");
  StackRoots _roots6({&str2});
  log("str2 = %p", str2);

  list2->append(str1);
  list2->append(str2);
  ASSERT_EQ(2, len(list2));
  ASSERT(str_equals(str1, list2->index_(0)));
  ASSERT(str_equals(str2, list2->index_(1)));

  PASS();
}

// Manual initialization.  This helped me write the GLOBAL_LIST() macro.
GlobalSlab<int, 3> _gSlab = {Tag::Global, 0, kZeroMask, kNoObjLen, {5, 6, 7}};
GlobalList<int, 3> _gList = {Tag::Global, 0, kZeroMask, kNoObjLen,
                             3,  // len
                             3,  // capacity
                             &_gSlab};
List<int>* gList = reinterpret_cast<List<int>*>(&_gList);

GLOBAL_LIST(int, 4, gList2, {5 COMMA 4 COMMA 3 COMMA 2});

GLOBAL_STR(gFoo, "foo");
GLOBAL_LIST(Str*, 2, gList3, {gFoo COMMA gFoo});

TEST test_global_list() {
  ASSERT_EQ(3, len(gList));
  ASSERT_EQ_FMT(5, gList->index_(0), "%d");
  ASSERT_EQ_FMT(6, gList->index_(1), "%d");
  ASSERT_EQ_FMT(7, gList->index_(2), "%d");

  ASSERT_EQ(4, len(gList2));
  ASSERT_EQ_FMT(5, gList2->index_(0), "%d");
  ASSERT_EQ_FMT(4, gList2->index_(1), "%d");
  ASSERT_EQ_FMT(3, gList2->index_(2), "%d");
  ASSERT_EQ_FMT(2, gList2->index_(3), "%d");

  ASSERT_EQ(2, len(gList3));
  ASSERT(str_equals(gFoo, gList3->index_(0)));
  ASSERT(str_equals(gFoo, gList3->index_(1)));

  PASS();
}

TEST test_list_funcs() {
  log("  ints");
  auto ints = NewList<int>({4, 5, 6});
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

  auto strs = NewList<Str*>();
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
  auto ints = NewList<int>({1, 2, 3});
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

TEST test_list_contains() {
  bool b;

  log("  List<Str*>");
  auto strs = NewList<Str*>();
  strs->append(StrFromC("bar"));

  b = list_contains(strs, StrFromC("foo"));
  ASSERT(b == false);

  strs->append(StrFromC("foo"));
  b = list_contains(strs, StrFromC("foo"));
  ASSERT(b == true);

  log("  ints");
  auto ints = NewList<int>({1, 2, 3});
  b = list_contains(ints, 1);
  ASSERT(b == true);

  b = list_contains(ints, 42);
  ASSERT(b == false);

  log("  floats");
  auto floats = NewList<double>({0.5, 0.25, 0.0});
  b = list_contains(floats, 0.0);
  log("b = %d", b);
  b = list_contains(floats, 42.0);
  log("b = %d", b);

  PASS();
}

TEST test_list_copy() {
  List<int>* a = NewList<int>(std::initializer_list<int>{1, 2, 3});
  List<int>* b = list(a);

  ASSERT_EQ(b->len_, a->len_);
  ASSERT_EQ(b->index_(0), a->index_(0));
  ASSERT_EQ(b->index_(1), a->index_(1));
  ASSERT_EQ(b->index_(2), a->index_(2));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(test_list_gc_header);
  RUN_TEST(test_global_list);

  RUN_TEST(test_list_funcs);
  RUN_TEST(test_list_iters);

  RUN_TEST(test_list_contains);
  RUN_TEST(test_list_copy);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
