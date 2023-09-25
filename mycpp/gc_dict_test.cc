#include "mycpp/gc_dict.h"

#include "mycpp/gc_mylib.h"
#include "vendor/greatest.h"

// Convenience function
template <typename K, typename V>
Dict<K, V>* NewDict() {
  return Alloc<Dict<K, V>>();
}

GLOBAL_STR(kStrFoo, "foo");
GLOBAL_STR(kStrBar, "bar");

TEST test_dict_init() {
  Str* s = StrFromC("foo");
  Str* s2 = StrFromC("bar");

  Dict<int, Str*>* d = Alloc<Dict<int, Str*>>(std::initializer_list<int>{42},
                                              std::initializer_list<Str*>{s});
  ASSERT_EQ(s, d->at(42));

  Dict<Str*, int>* d2 = Alloc<Dict<Str*, int>>(
      std::initializer_list<Str*>{s, s2}, std::initializer_list<int>{43, 99});
  ASSERT_EQ(43, d2->at(s));
  ASSERT_EQ(99, d2->at(s2));

  PASS();
}

TEST test_dict() {
  Dict<int, Str*>* d = NewDict<int, Str*>();

  // Regression: clear empty dict
  d->clear();

  d->set(1, StrFromC("foo"));
  log("d[1] = %s", d->at(1)->data_);

  auto d2 = NewDict<Str*, int>();
  Str* key = StrFromC("key");
  d2->set(key, 42);

  log("d2['key'] = %d", d2->at(key));
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

  ASSERT_EQ(10, d3->at(StrFromC("a")));
  ASSERT_EQ(11, d3->at(StrFromC("b")));
  ASSERT_EQ(12, d3->at(StrFromC("c")));
  ASSERT_EQ(3, len(d3));

  auto keys = sorted(d3);
  ASSERT(str_equals0("a", keys->at(0)));
  ASSERT(str_equals0("b", keys->at(1)));
  ASSERT(str_equals0("c", keys->at(2)));
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

  ASSERT_EQ_FMT(HeapTag::FixedSize, ObjHeader::FromObject(dict1)->heap_tag,
                "%d");
  ASSERT_EQ_FMT(HeapTag::FixedSize, ObjHeader::FromObject(dict1)->heap_tag,
                "%d");

  ASSERT_EQ_FMT(0, dict1->capacity_, "%d");
  ASSERT_EQ_FMT(0, dict2->capacity_, "%d");

  ASSERT_EQ(nullptr, dict1->index_);
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
  ASSERT_EQ(5, dict1->at(42));
  ASSERT_EQ(1, len(dict1));
#if 0
  ASSERT_EQ_FMT(6, dict1->capacity_, "%d");
#endif

#if 0
  ASSERT_EQ_FMT(32, ObjHeader::FromObject(dict1->index_)->obj_len, "%d");
  ASSERT_EQ_FMT(32, ObjHeader::FromObject(dict1->keys_)->obj_len, "%d");
  ASSERT_EQ_FMT(32, ObjHeader::FromObject(dict1->values_)->obj_len, "%d");
#endif

  dict1->set(42, 99);
  ASSERT_EQ(99, dict1->at(42));
  ASSERT_EQ(1, len(dict1));
#if 0
  ASSERT_EQ_FMT(6, dict1->capacity_, "%d");
#endif

  dict1->set(43, 10);
  ASSERT_EQ(10, dict1->at(43));
  ASSERT_EQ(2, len(dict1));
#if 0
  ASSERT_EQ_FMT(6, dict1->capacity_, "%d");
#endif

  for (int i = 0; i < 14; ++i) {
    dict1->set(i, 999);
    log("i = %d, capacity = %d", i, dict1->capacity_);

    // make sure we didn't lose old entry after resize
    ASSERT_EQ(10, dict1->at(43));
  }

  Str* foo = nullptr;
  Str* bar = nullptr;
  StackRoots _roots3({&foo, &bar});
  foo = StrFromC("foo");
  bar = StrFromC("bar");

  dict2->set(foo, bar);

  ASSERT_EQ(1, len(dict2));
  ASSERT(str_equals(bar, dict2->at(foo)));

#if 0
  ASSERT_EQ_FMT(32, ObjHeader::FromObject(dict2->index_)->obj_len, "%d");
  ASSERT_EQ_FMT(64, ObjHeader::FromObject(dict2->keys_)->obj_len, "%d");
  ASSERT_EQ_FMT(64, ObjHeader::FromObject(dict2->values_)->obj_len, "%d");
#endif

  auto dict_si = NewDict<Str*, int>();
  StackRoots _roots4({&dict_si});
  dict_si->set(foo, 42);
  ASSERT_EQ(1, len(dict_si));

#if 0
  ASSERT_EQ_FMT(32, ObjHeader::FromObject(dict_si->index_)->obj_len, "%d");
  ASSERT_EQ_FMT(64, ObjHeader::FromObject(dict_si->keys_)->obj_len, "%d");
  ASSERT_EQ_FMT(32, ObjHeader::FromObject(dict_si->values_)->obj_len, "%d");
#endif

  auto dict_is = NewDict<int, Str*>();
  StackRoots _roots5({&dict_is});
  dict_is->set(42, foo);
  PASS();

  ASSERT_EQ(1, len(dict_is));

#if 0
  ASSERT_EQ_FMT(32, ObjHeader::FromObject(dict_is->index_)->obj_len, "%d");
  ASSERT_EQ_FMT(32, ObjHeader::FromObject(dict_is->keys_)->obj_len, "%d");
  ASSERT_EQ_FMT(64, ObjHeader::FromObject(dict_is->values_)->obj_len, "%d");
#endif

  auto two = StrFromC("two");
  StackRoots _roots6({&two});

  auto dict3 =
      Alloc<Dict<int, Str*>>(std::initializer_list<int>{1, 2},
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

TEST dict_methods_test() {
  Dict<int, Str*>* d = nullptr;
  Dict<Str*, int>* d2 = nullptr;
  Str* key = nullptr;
  StackRoots _roots({&d, &d2, &key});

  d = Alloc<Dict<int, Str*>>();
  d->set(1, kStrFoo);
  ASSERT(str_equals0("foo", d->at(1)));

  d2 = Alloc<Dict<Str*, int>>();
  key = StrFromC("key");
  d2->set(key, 42);
  ASSERT_EQ(42, d2->at(key));

  PASS();

  d2->set(StrFromC("key2"), 2);
  d2->set(StrFromC("key3"), 3);

  ASSERT_EQ_FMT(3, len(d2), "%d");

  auto keys = d2->keys();
  ASSERT_EQ_FMT(3, len(keys), "%d");

  // Retain insertion order
  ASSERT(str_equals0("key", keys->at(0)));
  ASSERT(str_equals0("key2", keys->at(1)));
  ASSERT(str_equals0("key3", keys->at(2)));

  mylib::dict_erase(d2, StrFromC("key"));
  ASSERT_EQ_FMT(2, len(d2), "%d");

  auto keys2 = d2->keys();
  ASSERT_EQ_FMT(2, len(keys2), "%d");
  ASSERT(str_equals0("key2", keys2->at(0)));
  ASSERT(str_equals0("key3", keys2->at(1)));

  auto values = d2->values();
  ASSERT_EQ_FMT(2, len(values), "%d");
  ASSERT_EQ(2, values->at(0));
  ASSERT_EQ(3, values->at(1));

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
  auto a = StrFromC("a");

  d3->set(StrFromC("b"), 11);
  d3->set(StrFromC("c"), 12);
  d3->set(StrFromC("a"), 10);
  ASSERT_EQ(10, d3->at(StrFromC("a")));
  ASSERT_EQ(11, d3->at(StrFromC("b")));
  ASSERT_EQ(12, d3->at(StrFromC("c")));
  ASSERT_EQ(3, len(d3));

  auto keys3 = sorted(d3);
  ASSERT_EQ(3, len(keys3));
  ASSERT(str_equals0("a", keys3->at(0)));
  ASSERT(str_equals0("b", keys3->at(1)));
  ASSERT(str_equals0("c", keys3->at(2)));

  auto keys4 = d3->keys();
  ASSERT(list_contains(keys4, a));
  ASSERT(!list_contains(keys4, StrFromC("zzz")));

  ASSERT(dict_contains(d3, a));
  mylib::dict_erase(d3, a);
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

  mylib::dict_erase(ss, a);
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

TEST dict_iters_test() {
  Dict<Str*, int>* d2 = nullptr;
  List<Str*>* keys = nullptr;
  StackRoots _roots({&d2, &keys});

  d2 = Alloc<Dict<Str*, int>>();
  d2->set(kStrFoo, 2);
  d2->set(kStrBar, 3);

  keys = d2->keys();
  for (int i = 0; i < len(keys); ++i) {
    printf("k %s\n", keys->at(i)->data_);
  }

  log("  iterating over Dict");
  for (DictIter<Str*, int> it(d2); !it.Done(); it.Next()) {
    log("k = %s, v = %d", it.Key()->data_, it.Value());
  }

  PASS();
}

TEST test_tuple_construct() {
  auto kvs = Alloc<List<Tuple2<int, int>*>>();
  auto t1 = Alloc<Tuple2<int, int>>(0xdead, 0xbeef);
  auto t2 = Alloc<Tuple2<int, int>>(0xbeee, 0xeeef);
  kvs->append(t1);
  kvs->append(t2);

  auto d = dict(kvs);
  ASSERT_EQ(d->at(0xdead), 0xbeef);
  ASSERT_EQ(d->at(0xbeee), 0xeeef);

  PASS();
}

TEST test_update_dict() {
  auto d = Alloc<Dict<int, int>>();
  d->set(1, 0xdead);
  d->set(2, 0xbeef);
  ASSERT_EQ(d->at(1), 0xdead);
  ASSERT_EQ(d->at(2), 0xbeef);

  auto kvs = Alloc<List<Tuple2<int, int>*>>();
  auto t1 = Alloc<Tuple2<int, int>>(2, 0xfeeb);
  auto t2 = Alloc<Tuple2<int, int>>(3, 0x3333);
  kvs->append(t1);
  kvs->append(t2);
  d->update(kvs);
  ASSERT_EQ(d->at(1), 0xdead);
  ASSERT_EQ(d->at(2), 0xfeeb);
  ASSERT_EQ(d->at(3), 0x3333);

  PASS();
}

TEST test_tuple_key() {
  auto d1 = Alloc<Dict<Tuple2<int, int>*, int>>();
  auto t1 = Alloc<Tuple2<int, int>>(0xdead, 0xbeef);
  auto t2 = Alloc<Tuple2<int, int>>(0xbeee, 0xeeef);
  d1->set(t1, -42);
  d1->set(t2, 17);
  ASSERT_EQ(d1->at(t1), -42);
  ASSERT_EQ(d1->at(t2), 17);

  auto d2 = Alloc<Dict<Tuple2<Str*, int>*, int>>();
  auto t3 = Alloc<Tuple2<Str*, int>>(StrFromC("foo"), 0xbeef);
  auto t4 = Alloc<Tuple2<Str*, int>>(StrFromC("bar"), 0xeeef);
  d2->set(t3, 12345);
  d2->set(t4, 67890);
  ASSERT_EQ(d2->at(t3), 12345);
  ASSERT_EQ(d2->at(t4), 67890);

  PASS();
}

TEST test_dict_erase() {
  auto d = Alloc<Dict<int, int>>();
  d->set(25315, 0xdead);
  d->set(25316, 0xbeef);
  d->set(25317, 0xc0ffee);

  ASSERT_EQ(0xdead, d->index_(25315));
  ASSERT_EQ(0xbeef, d->index_(25316));
  ASSERT_EQ(0xc0ffee, d->index_(25317));

  mylib::dict_erase(d, 25315);
  ASSERT_FALSE(dict_contains(d, 25315));
  ASSERT_EQ(0xbeef, d->index_(25316));
  ASSERT_EQ(0xc0ffee, d->index_(25317));

  mylib::dict_erase(d, 25316);
  ASSERT_FALSE(dict_contains(d, 25316));
  ASSERT_EQ(0xc0ffee, d->index_(25317));

  // This is a trace of processes coming and going in a real shell. It tickles a
  // (now fixed) bug in dict_erase() that would prematurely open a slot in the
  // index before compacting the last inserted entry. With the right sequence of
  // collisions (hence this trace) this behavior can lead to an index slot that
  // points to an invalid entry, causing future calls to `find_key_in_index()`
  // to crash (e.g.  by dereferencing a bad pointer).
  d = Alloc<Dict<int, int>>();
  d->set(326224, 0);
  d->set(326225, 1);
  d->set(326226, 2);
  d->set(326227, 3);
  d->set(326228, 4);
  mylib::dict_erase(d, 326227);
  d->set(326229, 4);
  d->set(326230, 5);
  mylib::dict_erase(d, 326229);
  d->set(326231, 5);
  d->set(326232, 6);
  mylib::dict_erase(d, 326231);
  d->set(326233, 6);
  d->set(326234, 7);
  mylib::dict_erase(d, 326233);
  d->set(326235, 7);
  d->set(326236, 8);
  mylib::dict_erase(d, 326235);
  d->set(326237, 8);
  d->set(326238, 9);
  mylib::dict_erase(d, 326237);
  d->set(326239, 9);
  d->set(326240, 10);
  mylib::dict_erase(d, 326239);
  d->set(326241, 10);

  PASS();
}

// Ints hash to themselves, so we can control when collisions happen. This test
// sets up a few contrived workloads and checks that Dict still operates as
// expected.
TEST test_dict_probe() {
  auto d = Alloc<Dict<int, int>>();
  d->reserve(32);

  // First, fill the table to the brim and check that we can recall
  // everything.
  int n = d->capacity_;
  for (int i = 0; i < n; i++) {
    d->set(i, i);
  }
  ASSERT_EQ(n, d->capacity_);
  for (int i = 0; i < n; i++) {
    ASSERT_EQ(i, d->at(i));
  }
  // Triger a rehash, and check that everything is OK.
  d->set(n, n);
  ASSERT(d->capacity_ > n);
  for (int i = 0; i <= n; i++) {
    ASSERT_EQ(i, d->at(i));
  }
  for (int i = 0; i <= n; i++) {
    d->set(i, n * i);
  }
  for (int i = 0; i <= n; i++) {
    ASSERT_EQ(n * i, d->at(i));
  }

  // Reset and fill the table with keys that all has onto the same index slot
  n = d->capacity_;
  int target = n / 2;  // pick a slot in the middle to test wrap around
  d->clear();
  for (int i = 0; i < n; i++) {
    d->set(target * i, i);
  }
  // Remove each entry one-by-one, stopping after each removal to check that
  // the other keys can be set and retrieved without issue. This implicitly
  // checks that special index entires like tombstones are working correctly.
  for (int i = 0; i < n; i++) {
    mylib::dict_erase(d, target * i);
    for (int j = i + 1; j < n; j++) {
      d->set(target * j, j + 1);
      ASSERT_EQ(j + 1, d->at(target * j));
    }
  }

  PASS();
}

GLOBAL_DICT(gDict, int, int, 2, {42 COMMA 43}, {1 COMMA 2});

GLOBAL_DICT(gStrDict, Str*, Str*, 2, {kStrFoo COMMA kStrBar},
            {kStrBar COMMA kStrFoo});

TEST test_global_dict() {
  log("gDict len = %d", len(gDict));
  ASSERT_EQ(2, len(gDict));
  ASSERT_EQ(1, gDict->at(42));
  ASSERT_EQ(2, gDict->at(43));

  log("gStrDict len = %d", len(gStrDict));
  ASSERT_EQ(kStrFoo, gStrDict->at(kStrBar));
  ASSERT_EQ(kStrBar, gStrDict->at(kStrFoo));

  PASS();
}

TEST test_dict_ordering() {
  auto d = Alloc<Dict<int, int>>();

  auto in = NewList<int>(std::initializer_list<int>{95, 9, 67, 70, 93, 30, 25,
                                                    98, 80, 39, 56, 48, 99});
  for (ListIter<int> it(in); !it.Done(); it.Next()) {
    d->set(it.Value(), -1);
  }

  auto keys = d->keys();
  ASSERT_EQ(len(in), len(keys));
  for (int i = 0; i < len(in); i++) {
    ASSERT_EQ(in->index_(i), keys->index_(i));
  }

  // check that order survives rehashing
  d->reserve(2 * len(d));
  keys = d->keys();
  ASSERT_EQ(len(in), len(keys));
  for (int i = 0; i < len(in); i++) {
    ASSERT_EQ(in->index_(i), keys->index_(i));
  }

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
  RUN_TEST(test_tuple_construct);
  RUN_TEST(test_update_dict);
  RUN_TEST(test_tuple_key);
  RUN_TEST(test_dict_erase);
  RUN_TEST(test_global_dict);
  RUN_TEST(test_dict_ordering);
  RUN_TEST(test_dict_probe);

  RUN_TEST(dict_methods_test);
  RUN_TEST(dict_iters_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
