#include "mycpp/gc_list.h"

#include <assert.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>   // vprintf

#include "mycpp/common.h"
#include "mycpp/gc_alloc.h"  // gHeap
#include "mycpp/gc_obj.h"
#include "vendor/greatest.h"

using mylib::str_cmp;

GLOBAL_STR(kStrFoo, "foo");
GLOBAL_STR(kSpace, " ");

void Print(List<BigStr*>* parts) {
  log("---");
  log("len = %d", len(parts));
  for (int i = 0; i < len(parts); ++i) {
    BigStr* s = parts->at(i);
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
  auto list2 = NewList<BigStr*>();
  StackRoots _roots2({&list2});

  ASSERT_EQ(0, len(list1));
  ASSERT_EQ(0, len(list2));

  ASSERT_EQ_FMT(0, list1->capacity_, "%d");
  ASSERT_EQ_FMT(0, list2->capacity_, "%d");

  ASSERT_EQ_FMT(HeapTag::FixedSize, ObjHeader::FromObject(list1)->heap_tag,
                "%d");
  ASSERT_EQ_FMT(HeapTag::FixedSize, ObjHeader::FromObject(list2)->heap_tag,
                "%d");

#if 0
  // 8 byte obj header + 2 integers + pointer
  ASSERT_EQ_FMT(24, ObjHeader::FromObject(list1)->obj_len, "%d");
  ASSERT_EQ_FMT(24, ObjHeader::FromObject(list2)->obj_len, "%d");
#endif

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

  ASSERT_EQ_FMT(HeapTag::Opaque, ObjHeader::FromObject(list1->slab_)->heap_tag,
                "%d");

#if 0
  // 8 byte header + 3*4 == 8 + 12 == 20, rounded up to power of 2
  ASSERT_EQ_FMT(32, ObjHeader::FromObject(list1->slab_)->obj_len, "%d");
#endif

  ASSERT_EQ_FMT(11, list1->at(0), "%d");
  ASSERT_EQ_FMT(22, list1->at(1), "%d");
  ASSERT_EQ_FMT(33, list1->at(2), "%d");

  log("extending");
  auto more2 = NewList<int>(std::initializer_list<int>{44, 55, 66, 77});
  StackRoots _roots4({&more2});
  list1->extend(more2);

  ASSERT_EQ_FMT(7, len(list1), "%d");

#if 0
  // 8 bytes header + 7*4 == 8 + 28 == 36, rounded up to power of 2
  ASSERT_EQ_FMT(64, ObjHeader::FromObject(list1->slab_)->obj_len, "%d");
#endif

  ASSERT_EQ_FMT(11, list1->at(0), "%d");
  ASSERT_EQ_FMT(22, list1->at(1), "%d");
  ASSERT_EQ_FMT(33, list1->at(2), "%d");
  ASSERT_EQ_FMT(44, list1->at(3), "%d");
  ASSERT_EQ_FMT(55, list1->at(4), "%d");
  ASSERT_EQ_FMT(66, list1->at(5), "%d");
  ASSERT_EQ_FMT(77, list1->at(6), "%d");

  list1->append(88);
  ASSERT_EQ_FMT(88, list1->at(7), "%d");
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
  ASSERT(str_equals(str1, list2->at(0)));
  ASSERT(str_equals(str2, list2->at(1)));

  PASS();
}

// Manual initialization.  This helped me write the GLOBAL_LIST() macro.
GcGlobal<GlobalSlab<int, 3>> _gSlab = {
    .header = {0, kZeroMask, HeapTag::Global, kUndefinedId},
    {.items_ = {5, 6, 7}}};
GcGlobal<GlobalList<int, 3>> _gList = {
    .header = {0, kZeroMask, HeapTag::Global, kUndefinedId},
    {.len_ = 3, .capacity_ = 3, .slab_ = &_gSlab.obj}};
List<int>* gList = reinterpret_cast<List<int>*>(&_gList.obj);

GLOBAL_LIST(gList2, int, 4, {5 COMMA 4 COMMA 3 COMMA 2});

GLOBAL_STR(gFoo, "foo");
GLOBAL_LIST(gList3, BigStr*, 2, {gFoo COMMA gFoo});

TEST test_global_list() {
  ASSERT_EQ(3, len(gList));
  ASSERT_EQ_FMT(5, gList->at(0), "%d");
  ASSERT_EQ_FMT(6, gList->at(1), "%d");
  ASSERT_EQ_FMT(7, gList->at(2), "%d");

  ASSERT_EQ(4, len(gList2));
  ASSERT_EQ_FMT(5, gList2->at(0), "%d");
  ASSERT_EQ_FMT(4, gList2->at(1), "%d");
  ASSERT_EQ_FMT(3, gList2->at(2), "%d");
  ASSERT_EQ_FMT(2, gList2->at(3), "%d");

  ASSERT_EQ(2, len(gList3));
  ASSERT(str_equals(gFoo, gList3->at(0)));
  ASSERT(str_equals(gFoo, gList3->at(1)));

  PASS();
}

TEST test_list_funcs() {
  log("  ints");
  auto ints = NewList<int>({4, 5, 6});
  log("-- before pop(0)");
  for (int i = 0; i < len(ints); ++i) {
    log("ints[%d] = %d", i, ints->at(i));
  }
  ASSERT_EQ(3, len(ints));  // [4, 5, 6]
  ints->pop(0);             // [5, 6]

  ASSERT_EQ(2, len(ints));
  ASSERT_EQ_FMT(5, ints->at(0), "%d");
  ASSERT_EQ_FMT(6, ints->at(1), "%d");

  ints->reverse();
  ASSERT_EQ(2, len(ints));  // [6, 5]

  ASSERT_EQ_FMT(6, ints->at(0), "%d");
  ASSERT_EQ_FMT(5, ints->at(1), "%d");

  ints->append(9);  // [6, 5, 9]
  ASSERT_EQ(3, len(ints));

  ints->reverse();  // [9, 5, 6]
  ASSERT_EQ(9, ints->at(0));
  ASSERT_EQ(5, ints->at(1));
  ASSERT_EQ(6, ints->at(2));

  ints->set(0, 42);
  ints->set(1, 43);
  log("-- after mutation");
  for (int i = 0; i < len(ints); ++i) {
    log("ints[%d] = %d", i, ints->at(i));
  }

  auto L = list_repeat<BigStr*>(nullptr, 3);
  log("list_repeat length = %d", len(L));

  auto L2 = list_repeat<bool>(true, 3);
  log("list_repeat length = %d", len(L2));
  log("item 0 %d", L2->at(0));
  log("item 1 %d", L2->at(1));

  auto strs = NewList<BigStr*>();
  strs->append(StrFromC("c"));
  strs->append(StrFromC("a"));
  strs->append(StrFromC("b"));
  strs->append(kEmptyString);
  ASSERT_EQ(4, len(strs));  // ['c', 'a', 'b', '']

  strs->sort();
  ASSERT_EQ(4, len(strs));  // ['', 'a', 'b', 'c']
  ASSERT(str_equals(kEmptyString, strs->at(0)));
  ASSERT(str_equals(StrFromC("a"), strs->at(1)));
  ASSERT(str_equals(StrFromC("b"), strs->at(2)));
  ASSERT(str_equals(StrFromC("c"), strs->at(3)));

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

void ListFunc(std::initializer_list<BigStr*> init) {
  log("init.size() = %d", init.size());
}

TEST test_list_iters() {
  log("  forward iteration over list");
  auto ints = NewList<int>({1, 2, 3});
  for (ListIter<int> it(ints); !it.Done(); it.Next()) {
    int x = it.Value();
    log("x = %d", x);
  }

  {
    ListIter<int> it(ints);
    auto ints2 = list(it);
    ASSERT_EQ(ints->at(0), ints2->at(0));
    ASSERT_EQ(ints->at(1), ints2->at(1));
    ASSERT_EQ(ints->at(2), ints2->at(2));
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

TEST test_list_copy() {
  List<int>* a = NewList<int>(std::initializer_list<int>{1, 2, 3});
  List<int>* b = list(a);

  ASSERT_EQ(b->len_, a->len_);
  ASSERT_EQ(b->at(0), a->at(0));
  ASSERT_EQ(b->at(1), a->at(1));
  ASSERT_EQ(b->at(2), a->at(2));

  PASS();
}

TEST list_methods_test() {
  List<int>* ints = nullptr;
  StackRoots _roots({&ints});

  ints = NewList<int>(std::initializer_list<int>{5, 6, 7, 8});

  List<int>* slice1 = ints->slice(1);
  ASSERT_EQ(3, len(slice1));
  ASSERT_EQ(6, slice1->at(0));

  List<int>* slice2 = ints->slice(-4, -2);
  ASSERT_EQ(2, len(slice2));
  ASSERT_EQ(5, slice2->at(0));

  List<int>* slice3 = ints->slice(1, 4);
  ASSERT_EQ(3, len(slice3));
  ASSERT_EQ(6, slice3->at(0));
  ASSERT_EQ(7, slice3->at(1));
  ASSERT_EQ(8, slice3->at(2));

  log("-- before pop(0)");
  for (int i = 0; i < len(ints); ++i) {
    log("ints[%d] = %d", i, ints->at(i));
  }
  ASSERT_EQ(4, len(ints));  // [5, 6, 7, 8]

  log("pop()");

  ints->pop();  // [5, 6, 7]
  ASSERT_EQ(3, len(ints));
  ASSERT_EQ_FMT(5, ints->at(0), "%d");
  ASSERT_EQ_FMT(6, ints->at(1), "%d");
  ASSERT_EQ_FMT(7, ints->at(2), "%d");

  log("pop(0)");

  ints->pop(0);  // [6, 7]
  ASSERT_EQ(2, len(ints));
  ASSERT_EQ_FMT(6, ints->at(0), "%d");
  ASSERT_EQ_FMT(7, ints->at(1), "%d");

  ints->reverse();
  ASSERT_EQ(2, len(ints));  // [7, 6]

  ASSERT_EQ_FMT(7, ints->at(0), "%d");
  ASSERT_EQ_FMT(6, ints->at(1), "%d");

  ints->append(9);  // [7, 6, 9]
  ASSERT_EQ(3, len(ints));

  ints->reverse();  // [9, 6, 7]
  ASSERT_EQ(9, ints->at(0));
  ASSERT_EQ(6, ints->at(1));
  ASSERT_EQ(7, ints->at(2));

  auto other = NewList<int>(std::initializer_list<int>{-1, -2});
  ints->extend(other);  // [9, 6, 7, 1, 2]
  ASSERT_EQ(5, len(ints));
  ASSERT_EQ(-2, ints->at(4));
  ASSERT_EQ(-1, ints->at(3));

  ints->clear();
  ASSERT_EQ(0, len(ints));
  ASSERT_EQ(0, ints->slab_->items_[0]);  // make sure it's zero'd

  // Clear empty list
  auto empty = NewList<int*>();
  empty->clear();

  PASS();
}

TEST sort_test() {
  ASSERT_EQ(0, int_cmp(0, 0));
  ASSERT_EQ(-1, int_cmp(0, 5));
  ASSERT_EQ(1, int_cmp(0, -5));

  BigStr *a = nullptr, *aa = nullptr, *b = nullptr;
  StackRoots _roots({&a, &aa, &b});

  a = StrFromC("a");
  aa = StrFromC("aa");
  b = StrFromC("b");

  ASSERT_EQ(0, str_cmp(kEmptyString, kEmptyString));
  ASSERT_EQ(-1, str_cmp(kEmptyString, a));
  ASSERT_EQ(-1, str_cmp(a, aa));
  ASSERT_EQ(-1, str_cmp(a, b));

  ASSERT_EQ(1, str_cmp(b, a));
  ASSERT_EQ(1, str_cmp(b, kEmptyString));

  List<BigStr*>* strs = nullptr;
  StackRoots _roots2({&strs});
  strs = Alloc<List<BigStr*>>();

  strs->append(a);
  strs->append(aa);
  strs->append(b);
  strs->append(kEmptyString);
  ASSERT_EQ(4, len(strs));  // ['a', 'aa', 'b', '']

  strs->sort();  // ['', 'a', 'aa', 'b']
  ASSERT_EQ(4, len(strs));
  ASSERT(str_equals(kEmptyString, strs->at(0)));
  ASSERT(str_equals0("a", strs->at(1)));
  ASSERT(str_equals0("aa", strs->at(2)));
  ASSERT(str_equals0("b", strs->at(3)));

  PASS();
}

TEST contains_test() {
  BigStr* s = nullptr;
  BigStr* nul = nullptr;
  StackRoots _roots({&s, &nul});

  log("  List<BigStr*>");
  List<BigStr*>* strs = nullptr;
  List<int>* ints = nullptr;
  List<double>* floats = nullptr;

  StackRoots _roots2({&strs, &ints, &floats});

  strs = Alloc<List<BigStr*>>();

  strs->append(kSpace);
  s = StrFromC(" ");  // LOCAL space
  ASSERT(list_contains(strs, s));
  ASSERT(!list_contains(strs, kStrFoo));

  strs->append(kStrFoo);
  ASSERT(list_contains(strs, kStrFoo));

  log("  ints");
  ints = NewList<int>(std::initializer_list<int>{1, 2, 3});
  ASSERT(list_contains(ints, 1));

  ASSERT(!list_contains(ints, 42));

#if 0
  log("  floats");
  floats = NewList<double>(std::initializer_list<double>{0.5, 0.25, 0.0});
  ASSERT(list_contains(floats, 0.0));
  ASSERT(!list_contains(floats, 42.0));
#endif

  PASS();
}

TEST test_list_sort() {
  auto s1 = StrFromC("fooA");
  auto s2 = StrFromC("fooB");
  auto s3 = StrFromC("fooC");
  auto l = NewList<BigStr*>(std::initializer_list<BigStr*>{s3, s1, s2});

  auto s = sorted(l);
  ASSERT(str_equals(s->at(0), s1));
  ASSERT(str_equals(s->at(1), s2));
  ASSERT(str_equals(s->at(2), s3));

  PASS();
}

TEST test_list_remove() {
  auto l = NewList<int>(std::initializer_list<int>{1, 3, 3, 3, 2});

  for (int i = 0; i < 3; ++i) {
    l->remove(3);
  }

  bool caught = false;
  try {
    l->index(3);
  } catch (ValueError* e) {
    caught = true;
  }
  ASSERT(caught);

  ASSERT_EQ(l->at(0), 1);
  ASSERT_EQ(l->at(1), 2);

  PASS();
}

TEST test_list_pop_mem_safe() {
  auto l = NewList<int>();

  // List::pop(int) had a memory bug where it would buffer overflow due to a
  // mistake when calling memmove. To reproduce, the list had to be at least 16
  // items long, otherwise ASAN will not catch the error.
  for (int i = 0; i < 16; ++i) {
    l->append(i);
  }

  l->pop(15);  // This would cause a buffer overflow

  PASS();
}

TEST test_index_out_of_bounds() {
  auto l = NewList<int>({1, 2, 3});

  ASSERT_EQ(3, l->at(2));
  ASSERT_EQ(1, l->at(-3));

  bool caught;

  caught = false;
  try {
    l->at(3);
  } catch (IndexError* e) {
    caught = true;
  }
  ASSERT(caught);

  caught = false;
  try {
    l->at(-4);
  } catch (IndexError* e) {
    caught = true;
  }
  ASSERT(caught);

  // Now test setting it

  l->set(2, 10);
  l->set(-3, 11);

  ASSERT_EQ(10, l->at(2));
  ASSERT_EQ(11, l->at(-3));

  caught = false;
  try {
    l->set(3, 12);
  } catch (IndexError* e) {
    caught = true;
  }
  ASSERT(caught);

  caught = false;
  try {
    l->set(-4, 13);
  } catch (IndexError* e) {
    caught = true;
  }
  ASSERT(caught);

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

  RUN_TEST(list_methods_test);
  RUN_TEST(sort_test);
  RUN_TEST(contains_test);

  RUN_TEST(test_list_copy);
  RUN_TEST(test_list_sort);
  RUN_TEST(test_list_remove);

  RUN_TEST(test_list_pop_mem_safe);

  RUN_TEST(test_index_out_of_bounds);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
