#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST test_dict_init() {
  Str* s = StrFromC("foo");
  Dict<int, Str*>* d = NewDict<int, Str*>({42}, {s});
  ASSERT_EQ(s, d->index_(42));

  PASS();
}

TEST test_dict() {
  Dict<int, Str*>* d = NewDict<int, Str*>();
  d->set(1, StrFromC("foo"));
  log("d[1] = %s", d->index_(1)->data_);

  auto d2 = NewDict<Str*, int>();
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

  ASSERT(dict_contains(d, 1));
  ASSERT(!dict_contains(d, 423));

  Str* v1 = d->get(1);
  log("v1 = %s", v1->data_);
  ASSERT(str_equals0("foo", v1));

  Str* v2 = d->get(423);  // nonexistent
  ASSERT_EQ(nullptr, v2);
  log("v2 = %p", v2);

  auto d3 = NewDict<Str*, int>();
  ASSERT_EQ(0, len(d3));

  auto a = StrFromC("a");

  d3->set(StrFromC("b"), 11);
  ASSERT_EQ(1, len(d3));

  d3->set(StrFromC("c"), 12);
  ASSERT_EQ(2, len(d3));

  d3->set(StrFromC("a"), 10);
  ASSERT_EQ(3, len(d3));

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
  mylib::dict_erase(d3, a);
  ASSERT(!dict_contains(d3, a));
  ASSERT_EQ(2, len(d3));

  // Test removed item
  for (DictIter<Str*, int> it(d3); !it.Done(); it.Next()) {
    auto key = it.Key();
    printf("d3 key = ");
    print(key);
  }

  // Test a different type of dict, to make sure partial template
  // specialization works
  auto ss = NewDict<Str*, Str*>();
  ss->set(a, a);
  ASSERT_EQ(1, len(ss));

  ASSERT_EQ(1, len(ss->keys()));
  ASSERT_EQ(1, len(ss->values()));

  mylib::dict_erase(ss, a);
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

// TODO:
// - Test set() can resize the dict
//   - I guess you have to do rehashing?

TEST test_dict_internals() {
  auto dict1 = NewDict<int, int>();
  StackRoots _roots1({&dict1});
  auto dict2 = NewDict<Str*, Str*>();
  StackRoots _roots2({&dict2});

  ASSERT_EQ(0, len(dict1));
  ASSERT_EQ(0, len(dict2));

  ASSERT_EQ_FMT(HeapTag::FixedSize, dict1->header_.heap_tag, "%d");
  ASSERT_EQ_FMT(HeapTag::FixedSize, dict1->header_.heap_tag, "%d");

  ASSERT_EQ_FMT(0, dict1->capacity_, "%d");
  ASSERT_EQ_FMT(0, dict2->capacity_, "%d");

  ASSERT_EQ(nullptr, dict1->entry_);
  ASSERT_EQ(nullptr, dict1->keys_);
  ASSERT_EQ(nullptr, dict1->values_);

  // Make sure they're on the heap
#ifndef MARK_SWEEP
  int diff1 = reinterpret_cast<char*>(dict1) - gHeap.from_space_.begin_;
  int diff2 = reinterpret_cast<char*>(dict2) - gHeap.from_space_.begin_;
  ASSERT(diff1 < 1024);
  ASSERT(diff2 < 1024);
#endif

  dict1->set(42, 5);
  ASSERT_EQ(5, dict1->index_(42));
  ASSERT_EQ(1, len(dict1));
  ASSERT_EQ_FMT(6, dict1->capacity_, "%d");

#if 0
  ASSERT_EQ_FMT(32, dict1->entry_->header_.obj_len, "%d");
  ASSERT_EQ_FMT(32, dict1->keys_->header_.obj_len, "%d");
  ASSERT_EQ_FMT(32, dict1->values_->header_.obj_len, "%d");
#endif

  dict1->set(42, 99);
  ASSERT_EQ(99, dict1->index_(42));
  ASSERT_EQ(1, len(dict1));
  ASSERT_EQ_FMT(6, dict1->capacity_, "%d");

  dict1->set(43, 10);
  ASSERT_EQ(10, dict1->index_(43));
  ASSERT_EQ(2, len(dict1));
  ASSERT_EQ_FMT(6, dict1->capacity_, "%d");

  for (int i = 0; i < 14; ++i) {
    dict1->set(i, 999);
    log("i = %d, capacity = %d", i, dict1->capacity_);

    // make sure we didn't lose old entry after resize
    ASSERT_EQ(10, dict1->index_(43));
  }

  Str* foo = nullptr;
  Str* bar = nullptr;
  StackRoots _roots3({&foo, &bar});
  foo = StrFromC("foo");
  bar = StrFromC("bar");

  dict2->set(foo, bar);

  ASSERT_EQ(1, len(dict2));
  ASSERT(str_equals(bar, dict2->index_(foo)));

#if 0
  ASSERT_EQ_FMT(32, dict2->entry_->header_.obj_len, "%d");
  ASSERT_EQ_FMT(64, dict2->keys_->header_.obj_len, "%d");
  ASSERT_EQ_FMT(64, dict2->values_->header_.obj_len, "%d");
#endif

  auto dict_si = NewDict<Str*, int>();
  StackRoots _roots4({&dict_si});
  dict_si->set(foo, 42);
  ASSERT_EQ(1, len(dict_si));

#if 0
  ASSERT_EQ_FMT(32, dict_si->entry_->header_.obj_len, "%d");
  ASSERT_EQ_FMT(64, dict_si->keys_->header_.obj_len, "%d");
  ASSERT_EQ_FMT(32, dict_si->values_->header_.obj_len, "%d");
#endif

  auto dict_is = NewDict<int, Str*>();
  StackRoots _roots5({&dict_is});
  dict_is->set(42, foo);
  PASS();

  ASSERT_EQ(1, len(dict_is));

#if 0
  ASSERT_EQ_FMT(32, dict_is->entry_->header_.obj_len, "%d");
  ASSERT_EQ_FMT(32, dict_is->keys_->header_.obj_len, "%d");
  ASSERT_EQ_FMT(64, dict_is->values_->header_.obj_len, "%d");
#endif

  auto two = StrFromC("two");
  StackRoots _roots6({&two});

  auto dict3 =
      NewDict<int, Str*>(std::initializer_list<int>{1, 2},
                         std::initializer_list<Str*>{kEmptyString, two});
  StackRoots _roots7({&dict3});

  ASSERT_EQ_FMT(2, len(dict3), "%d");
  ASSERT(str_equals(kEmptyString, dict3->get(1)));
  ASSERT(str_equals(two, dict3->get(2)));

  PASS();
}

TEST test_empty_dict() {
  auto d = Alloc<Dict<Str*, Str*>>();

  // Look up in empty dict
  Str* val = d->get(StrFromC("nonexistent"));
  log("val %p", val);
  ASSERT_EQ(nullptr, val);

  Str* val2 = d->get(StrFromC("nonexistent"), kEmptyString);
  ASSERT_EQ(kEmptyString, val2);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(test_dict_init);
  RUN_TEST(test_dict);
  RUN_TEST(test_dict_internals);
  RUN_TEST(test_empty_dict);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
