// Unit tests for gc_heap

// More tests to do:
//
// - Integrate with ASDL and use the pretty printer.
//
// - Integrate with mycpp and run mycpp/examples/
//   - Make sure the benchmarks show less heap usage.

#include "mycpp/error_types.h"
#include "mycpp/gc_builtins.h"
#include "mycpp/gc_containers.h"

#include "vendor/greatest.h"

// Types

// Constants

// Functions

// Variables

#ifdef GC_STATS
  #define ASSERT_NUM_LIVE_OBJS(x) ASSERT_EQ_FMT((x), gHeap.num_live_objs_, "%d")
#else
  #define ASSERT_NUM_LIVE_OBJS(x)
#endif

// Hm we're getting a warning because these aren't plain old data?
// https://stackoverflow.com/questions/1129894/why-cant-you-use-offsetof-on-non-pod-structures-in-c
// https://stackoverflow.com/questions/53850100/warning-offset-of-on-non-standard-layout-type-derivedclass

// The structures must be layout compatible!  Protect against typos.
static_assert(offsetof(Str, data_) == offsetof(GlobalStr<1>, data_),
              "Str and GlobalStr should be consistent");

static_assert(offsetof(Slab<int>, items_) ==
                  offsetof(GlobalSlab<int COMMA 1>, items_),
              "Slab and GlobalSlab should be consistent");

static_assert(kSlabHeaderSize == offsetof(GlobalSlab<int COMMA 1>, items_),
              "kSlabHeaderSize and GlobalSlab should be consistent");

static_assert(offsetof(List<int>, slab_) ==
                  offsetof(GlobalList<int COMMA 1>, slab_),
              "List and GlobalList should be consistent");

// 1 MiB, and will double when necessary.  Note: femtolisp uses 512 KiB.
const int kInitialSize = 1 << 20;

// TODO(Jesse): Gross.  Put this somewhere so we don't have to copy it here.
//
// COPY of what's in gc_heap.cc for testing.  This is 16 bytes.
// The empty string is 12 + 1 = 13 bytes.  But we round up with aligned().
// TODO: We could avoid the 3 aligned() calls by changing the definition of
// obj_len_.  We could use the OCaml trick of numbers after the NUL byte.

class LayoutForwarded : public Obj {
 public:
  Obj* new_location;  // valid if and only if heap_tag_ == Tag::Forwarded
};

TEST test_str_creation() {
  Str* s = StrFromC("foo");
  ASSERT_EQ(3, len(s));
  ASSERT_EQ(0, strcmp("foo", s->data_));

  // String with internal NUL
  Str* s2 = StrFromC("foo\0bar", 7);
  ASSERT_EQ(7, len(s2));
  ASSERT_EQ(0, memcmp("foo\0bar\0", s2->data_, 8));

  Str* s3 = AllocStr(1);
  ASSERT_EQ(1, len(s3));
  ASSERT_EQ(0, memcmp("\0\0", s3->data_, 2));

  // Test truncating a string
  Str* s4 = OverAllocatedStr(7);
  // LENGTH IS NOT YET SET -- CALLER IS RESPONSIBLE
  // ASSERT_EQ(7, len(s4));
  ASSERT_EQ(0, memcmp("\0\0\0\0\0\0\0\0", s4->data_, 8));

  // Hm annoying that we have to do a const_cast
  memcpy(s4->data(), "foo", 3);
  strcpy(s4->data(), "foo");
  s4->SetObjLenFromStrLen(3);

  ASSERT_EQ(3, len(s4));
  ASSERT_EQ(0, strcmp("foo", s4->data_));

  PASS();
}

// Doesn't really test anything
TEST sizeof_test() {
  log("");

  // 24 = 4 + (4 + 4 + 4) + 8
  // Feels like a small string optimization here would be nice.
  log("sizeof(Str) = %d", sizeof(Str));
  // 16 = 4 + pad4 + 8
  log("sizeof(List) = %d", sizeof(List<int>));
  // 32 = 4 + pad4 + 8 + 8 + 8
  log("sizeof(Dict) = %d", sizeof(Dict<int, int>));

  // 8 byte sheader
  log("sizeof(Obj) = %d", sizeof(Obj));
  // 8 + 128 possible entries
  // log("sizeof(LayoutFixed) = %d", sizeof(LayoutFixed));

  log("sizeof(Heap) = %d", sizeof(Heap));

  int min_obj_size = sizeof(LayoutForwarded);
  int short_str_size = aligned(kStrHeaderSize + 1);

  log("kStrHeaderSize = %d", kStrHeaderSize);
  log("aligned(kStrHeaderSize + 1) = %d", short_str_size);
  log("sizeof(LayoutForwarded) = %d", min_obj_size);

  ASSERT(min_obj_size <= short_str_size);

  char* p = static_cast<char*>(gHeap.Allocate(17));
  char* q = static_cast<char*>(gHeap.Allocate(9));
  log("p = %p", p);
  log("q = %p", q);

  PASS();
}

// TODO: the last one overflows
int sizes[] = {0, 1,  2,  3,   4,   5,       8,
               9, 12, 16, 256, 257, 1 << 30, (1 << 30) + 1};
int nsizes = sizeof(sizes) / sizeof(sizes[0]);

TEST roundup_test() {
  for (int i = 0; i < nsizes; ++i) {
    int n = sizes[i];
    log("%d -> %d", n, RoundUp(n));
  }

  PASS();
}

// TODO:
// - Test what happens when a new string goes over the max heap size
//   - We want to resize the to_space, trigger a GC, and then allocate?  Or is
//     there something simpler?

GLOBAL_STR(str4, "egg");

TEST str_test() {
  ASSERT(str_equals(kEmptyString, kEmptyString));

  Str* str1 = nullptr;
  Str* str2 = nullptr;
  StackRoots _roots({&str1, &str2});

  str1 = StrFromC("");
  str2 = StrFromC("one\0two", 7);

  ASSERT_EQ_FMT(Tag::Opaque, str1->heap_tag_, "%d");
  ASSERT_EQ_FMT(kStrHeaderSize + 1, str1->obj_len_, "%d");
  ASSERT_EQ_FMT(kStrHeaderSize + 7 + 1, str2->obj_len_, "%d");

  // Make sure they're on the heap
  int diff1 = reinterpret_cast<char*>(str1) - gHeap.from_space_.begin_;
  int diff2 = reinterpret_cast<char*>(str2) - gHeap.from_space_.begin_;
  ASSERT(diff1 < 1024);
  ASSERT(diff2 < 1024);

  ASSERT_EQ(0, len(str1));
  ASSERT_EQ(7, len(str2));

  // Global strings

  ASSERT_EQ('e', str4->data_[0]);
  ASSERT_EQ('g', str4->data_[1]);
  ASSERT_EQ('g', str4->data_[2]);
  ASSERT_EQ('\0', str4->data_[3]);
  ASSERT_EQ(Tag::Global, str4->heap_tag_);
  ASSERT_EQ(16, str4->obj_len_);
  ASSERT_EQ(3, len(str4));

  PASS();
}

// TODO:
//
// - Test what happens append() runs over the max heap size
//   - how does it trigger a collection?

TEST list_test() {
  auto list1 = NewList<int>();
  StackRoots _roots1({&list1});
  auto list2 = NewList<Str*>();
  StackRoots _roots2({&list2});

  ASSERT_EQ(0, len(list1));
  ASSERT_EQ(0, len(list2));

  ASSERT_EQ_FMT(0, list1->capacity_, "%d");
  ASSERT_EQ_FMT(0, list2->capacity_, "%d");

  ASSERT_EQ_FMT(Tag::FixedSize, list1->heap_tag_, "%d");
  ASSERT_EQ_FMT(Tag::FixedSize, list2->heap_tag_, "%d");

  // 8 byte obj header + 2 integers + pointer
  ASSERT_EQ_FMT(24, list1->obj_len_, "%d");
  ASSERT_EQ_FMT(24, list2->obj_len_, "%d");

  // Make sure they're on the heap
  int diff1 = reinterpret_cast<char*>(list1) - gHeap.from_space_.begin_;
  int diff2 = reinterpret_cast<char*>(list2) - gHeap.from_space_.begin_;
  ASSERT(diff1 < 1024);
  ASSERT(diff2 < 1024);

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

  int d_slab = reinterpret_cast<char*>(list1->slab_) - gHeap.from_space_.begin_;
  ASSERT(d_slab < 1024);

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

TEST list_repro() {
  // For isolation

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

TEST global_list_test() {
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

// TODO:
// - Test set() can resize the dict
//   - I guess you have to do rehashing?

TEST dict_test() {
  auto dict1 = NewDict<int, int>();
  StackRoots _roots1({&dict1});
  auto dict2 = NewDict<Str*, Str*>();
  StackRoots _roots2({&dict2});

  ASSERT_EQ(0, len(dict1));
  ASSERT_EQ(0, len(dict2));

  ASSERT_EQ_FMT(Tag::FixedSize, dict1->heap_tag_, "%d");
  ASSERT_EQ_FMT(Tag::FixedSize, dict1->heap_tag_, "%d");

  ASSERT_EQ_FMT(0, dict1->capacity_, "%d");
  ASSERT_EQ_FMT(0, dict2->capacity_, "%d");

  ASSERT_EQ(nullptr, dict1->entry_);
  ASSERT_EQ(nullptr, dict1->keys_);
  ASSERT_EQ(nullptr, dict1->values_);

  // Make sure they're on the heap
  int diff1 = reinterpret_cast<char*>(dict1) - gHeap.from_space_.begin_;
  int diff2 = reinterpret_cast<char*>(dict2) - gHeap.from_space_.begin_;
  ASSERT(diff1 < 1024);
  ASSERT(diff2 < 1024);

  dict1->set(42, 5);
  ASSERT_EQ(5, dict1->index_(42));
  ASSERT_EQ(1, len(dict1));
  ASSERT_EQ_FMT(6, dict1->capacity_, "%d");

  ASSERT_EQ_FMT(32, dict1->entry_->obj_len_, "%d");
  ASSERT_EQ_FMT(32, dict1->keys_->obj_len_, "%d");
  ASSERT_EQ_FMT(32, dict1->values_->obj_len_, "%d");

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

  ASSERT_EQ_FMT(32, dict2->entry_->obj_len_, "%d");
  ASSERT_EQ_FMT(64, dict2->keys_->obj_len_, "%d");
  ASSERT_EQ_FMT(64, dict2->values_->obj_len_, "%d");

  auto dict_si = NewDict<Str*, int>();
  StackRoots _roots4({&dict_si});
  dict_si->set(foo, 42);
  ASSERT_EQ(1, len(dict_si));

  ASSERT_EQ_FMT(32, dict_si->entry_->obj_len_, "%d");
  ASSERT_EQ_FMT(64, dict_si->keys_->obj_len_, "%d");
  ASSERT_EQ_FMT(32, dict_si->values_->obj_len_, "%d");

  auto dict_is = NewDict<int, Str*>();
  StackRoots _roots5({&dict_is});
  dict_is->set(42, foo);
  PASS();

  ASSERT_EQ(1, len(dict_is));

  ASSERT_EQ_FMT(32, dict_is->entry_->obj_len_, "%d");
  ASSERT_EQ_FMT(32, dict_is->keys_->obj_len_, "%d");
  ASSERT_EQ_FMT(64, dict_is->values_->obj_len_, "%d");

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

TEST dict_repro() {
  // For isolation

  PASS();
}

class Point : public Obj {
 public:
  Point(int x, int y)
      : Obj(Tag::Opaque, kZeroMask, sizeof(Point)), x_(x), y_(y) {
  }
  int size() {
    return x_ + y_;
  }
  int x_;
  int y_;
};

const int kLineMask = 0x3;  // 0b0011

class Line : public Obj {
 public:
  Line()
      : Obj(Tag::FixedSize, kLineMask, sizeof(Line)),
        begin_(nullptr),
        end_(nullptr) {
  }
  Point* begin_;
  Point* end_;
};

TEST fixed_trace_test() {
  gHeap.Init(kInitialSize);  // reset the whole thing

  ASSERT_NUM_LIVE_OBJS(0);

  Point* p = nullptr;
  Point* p2 = nullptr;
  Line* line = nullptr;

  StackRoots _roots({&p, &p2, &line});

  p = Alloc<Point>(3, 4);
  log("point size = %d", p->size());

  ASSERT_NUM_LIVE_OBJS(1);

  line = Alloc<Line>();

  p2 = Alloc<Point>(5, 6);
  line->begin_ = p;

  // ROOTING ISSUE: This isn't valid?  Uncomment and we'll see a crash in
  // testgc mode.

  // line->end_ = Alloc<Point>(5, 6);

  // I think the problem is that the allocation causes the LHS to be invalid?

  line->end_ = p2;

  ASSERT_NUM_LIVE_OBJS(3);

  gHeap.Collect();
  ASSERT_NUM_LIVE_OBJS(3);

  // remove last reference
  line->end_ = nullptr;
  p2 = nullptr;

  gHeap.Collect();
  ASSERT_NUM_LIVE_OBJS(2);

  PASS();
}

TEST slab_trace_test() {
  gHeap.Init(kInitialSize);  // reset the whole thing

  ASSERT_NUM_LIVE_OBJS(0);

  {
    List<int>* ints = nullptr;
    StackRoots _roots({&ints});
    ints = Alloc<List<int>>();
    ASSERT_NUM_LIVE_OBJS(1);

    ints->append(3);
    ASSERT_NUM_LIVE_OBJS(2);
  }  // ints goes out of scope

  gHeap.Collect();
  ASSERT_NUM_LIVE_OBJS(0);

  List<Str*>* strings = nullptr;
  Str* tmp = nullptr;
  StackRoots _roots({&strings, &tmp});

  // List of strings
  strings = Alloc<List<Str*>>();
  ASSERT_NUM_LIVE_OBJS(1);

  // +2: slab and string
  tmp = StrFromC("yo");
  strings->append(tmp);
  ASSERT_NUM_LIVE_OBJS(3);

  // +1 string
  tmp = StrFromC("bar");
  strings->append(tmp);
  ASSERT_NUM_LIVE_OBJS(4);

  // -1: remove reference to "bar"
  strings->set(1, nullptr);
  tmp = nullptr;
  gHeap.Collect();
  ASSERT_NUM_LIVE_OBJS(3);

  // -1: set to GLOBAL instance.  Remove reference to "yo".
  strings->set(0, str4);
  gHeap.Collect();
  ASSERT_NUM_LIVE_OBJS(2);

  PASS();
}

TEST global_trace_test() {
  gHeap.Init(kInitialSize);

  Str* l4 = nullptr;
  List<Str*>* strings = nullptr;

  StackRoots _roots({&l4, &strings});

  l4 = str4;
  ASSERT_NUM_LIVE_OBJS(0);

  gHeap.Collect();
  ASSERT_NUM_LIVE_OBJS(0);

  // Heap reference to global

  strings = Alloc<List<Str*>>();
  ASSERT_NUM_LIVE_OBJS(1);

  // We now have the Slab too
  strings->append(nullptr);
  ASSERT_NUM_LIVE_OBJS(2);

  // Global pointer doesn't increase the count
  strings->set(1, str4);
  ASSERT_NUM_LIVE_OBJS(2);

  // Not after GC either
  gHeap.Collect();
  ASSERT_NUM_LIVE_OBJS(2);

  PASS();
}

void ShowRoots(const Heap& heap) {
  log("--");
  for (int i = 0; i < heap.roots_top_; ++i) {
    log("%d. %p", i, heap.roots_[i]);
    // This is NOT on the heap; it's on the stack.
    // int diff1 = reinterpret_cast<char*>(heap.roots[i]) - gHeap.from_space_;
    // assert(diff1 < 1024);

    Obj** h = heap.roots_[i];
    Obj* raw = *h;
    log("   %p", raw);

    // Raw pointer is on the heap.
    int diff2 = reinterpret_cast<char*>(raw) - gHeap.from_space_.begin_;
    // log("diff2 = %d", diff2);
    assert(diff2 < 2048);

    // This indeed mutates it and causes a crash
    // h->Update(nullptr);
  }
}

Str* myfunc() {
  Local<Str> str1(StrFromC("foo"));
  Local<Str> str2(StrFromC("foo"));
  Local<Str> str3(StrFromC("foo"));

  log("myfunc roots_top = %d", gHeap.roots_top_);
  ShowRoots(gHeap);

  return str1;  // implicit conversion to raw pointer
}

void otherfunc(Local<Str> s) {
  log("otherfunc roots_top_ = %d", gHeap.roots_top_);
  log("len(s) = %d", len(s));
}

void paramfunc(Param<Str> s) {
  log("paramfunc roots_top_ = %d", gHeap.roots_top_);
  log("len(s) = %d", len(s));
}

#if 0
TEST local_test() {
  gHeap.Init(kInitialSize);  // reset the whole thing

  {
    log("top = %d", gHeap.roots_top_);
    ASSERT_EQ(0, gHeap.roots_top_);

    auto point = Alloc<Point>(3, 4);
    Local<Point> p(point);
    ASSERT_EQ(1, gHeap.roots_top_);

    log("point.x = %d", p->x_);  // invokes operator->

    // invokes operator*, but I don't think we need it!
    // log("point.y = %d", (*p).y_);

    Local<Str> str2(StrFromC("bar"));
    ASSERT_EQ(2, gHeap.roots_top_);

    myfunc();

    otherfunc(str2);
    ASSERT_EQ_FMT(2, gHeap.roots_top_, "%d");

    paramfunc(str2);
    ASSERT_EQ_FMT(2, gHeap.roots_top_, "%d");

    ShowRoots(gHeap);

    gHeap.Collect();

    // This uses implicit convertion from T* to Local<T>, which is OK!  Reverse
    // is not OK.
    Local<Point> p2 = point;
    ASSERT_EQ_FMT(3, gHeap.roots_top_, "%d");

    Local<Point> p3;
    ASSERT_EQ_FMT(3, gHeap.roots_top_, "%d");
    p3 = p2;
    ASSERT_EQ_FMT(4, gHeap.roots_top_, "%d");
  }
  ASSERT_EQ_FMT(0, gHeap.roots_top_, "%d");

  // Hm this calls copy constructor!
  Local<Point> p4 = nullptr;

  Param<Point> p5 = p4;

  PASS();
}
#endif

class Base {
 public:
  Base(int a) : a_(a) {
  }
  int a_;
};

class Derived : public Base {
 public:
  Derived(int a, int b) : Base(a), b_(b) {
  }
  int b_;
};

int base_func(Base* base) {
  return base->a_;
}

int base_func_local(Local<Base> base) {
  return base->a_;
}

#if 0
TEST local_variance_test() {
  Base i1(5);
  log("i1.a_ = %d", i1.a_);

  Derived i2(3, 4);
  log("i2 = %d %d", i2.a_, i2.b_);

  ASSERT_EQ(5, base_func(&i1));
  ASSERT_EQ(3, base_func(&i2));

  Local<Base> h1 = &i1;
  // Does NOT work
  // Local<Base> h2 = i2;
  Local<Derived> h2 = &i2;

  ASSERT_EQ(5, base_func_local(h1));
  // Variance doesn't work!  Bad!  So we don't want to use Local<T>.
  // ASSERT_EQ(3, base_func_local(h2));

  PASS();
}
#endif

TEST stack_roots_test() {
  Str* s = nullptr;
  List<int>* L = nullptr;

  gHeap.Init(kInitialSize);  // reset the whole thing

  ASSERT_EQ(0, gHeap.roots_top_);

  StackRoots _roots({&s, &L});

  s = StrFromC("foo");
  // L = nullptr;
  L = NewList<int>();

  ASSERT_EQ_FMT(2, gHeap.roots_top_, "%d");

  PASS();
}

void ShowSlab(Obj* obj) {
  assert(obj->heap_tag_ == Tag::Scanned);
  auto slab = reinterpret_cast<Slab<void*>*>(obj);

  int n = (slab->obj_len_ - kSlabHeaderSize) / sizeof(void*);
  log("slab len = %d, n = %d", slab->obj_len_, n);
  for (int i = 0; i < n; ++i) {
    void* p = slab->items_[i];
    if (p == nullptr) {
      log("p = nullptr");
    } else {
      log("p = %p", p);
    }
  }
}

// Prints field masks for Dict and List
TEST field_mask_test() {
  auto L = NewList<int>();
  StackRoots _roots({&L});

  L->append(1);
  log("List mask = %d", L->field_mask_);

  auto d = Alloc<Dict<Str*, int>>();
  StackRoots _roots2({&d});

  auto key = StrFromC("foo");
  StackRoots _roots9({&key});
  d->set(key, 3);

  // oops this is bad?  Because StrFromC() might move d in the middle of the
  // expression!  Gah!
  // d->set(StrFromC("foo"), 3);

  log("Dict mask = %d", d->field_mask_);

#if GC_STATS
  ShowFixedChildren(L);
  ShowFixedChildren(d);
#endif

  auto L2 = NewList<Str*>();
  StackRoots _roots3({&L2});

  auto s = StrFromC("foo");
  StackRoots _roots4({&s});

  L2->append(s);
  L2->append(s);
  ShowSlab(L2->slab_);

  PASS();
}

#if 0
TEST repro2() {
  auto d = Alloc<Dict<Str*, int>>();
  StackRoots _roots2({&d});

  auto key = StrFromC("foo");
  StackRoots _roots9({&key});
  d->set(key, 3);

  PASS();
}
#endif

TEST compile_time_masks_test() {
  // Note: These will be different for 32 bit

  ASSERT_EQ(offsetof(List<int>, slab_),
            offsetof(GlobalList<int COMMA 1>, slab_));
  // 0b 0000 0010
  ASSERT_EQ_FMT(0x0002, maskof_List(), "0x%x");

  // https://stackoverflow.com/questions/13842468/comma-in-c-c-macro
  // There is a trick with __VA_ARGS__ I don't understand.

  ASSERT_EQ(offsetof(Dict<int COMMA int>, entry_),
            offsetof(_DummyDict, entry_));
  ASSERT_EQ(offsetof(Dict<int COMMA int>, keys_), offsetof(_DummyDict, keys_));
  ASSERT_EQ(offsetof(Dict<int COMMA int>, values_),
            offsetof(_DummyDict, values_));

  // in binary: 0b 0000 0000 0000 01110
  ASSERT_EQ_FMT(0x000E, maskof_Dict(), "0x%x");

  PASS();
}

// 8 byte vtable, 8 byte Obj header, then member_
class BaseObj : public Obj {
 public:
  BaseObj(int obj_len) : Obj(Tag::Opaque, kZeroMask, obj_len) {
  }
  BaseObj() : BaseObj(sizeof(BaseObj)) {
  }

  virtual int Method() {
    return 3;
  }
  int member_ = 254;
};

// 8 byte vtable, 8 byte Obj header, then member_, then derived_member_
class DerivedObj : public BaseObj {
 public:
  DerivedObj() : BaseObj(sizeof(DerivedObj)) {
  }
  virtual int Method() {
    return 4;
  }

  int derived_member_ = 253;
  int derived_member2_ = 252;
};

void ShowObj(Obj* obj) {
  log("obj->heap_tag_ %d", obj->heap_tag_);
  log("obj->obj_len_ %d", obj->obj_len_);
}

TEST vtable_test() {
  DerivedObj d3;
  BaseObj* b3 = &d3;
  log("method = %d", b3->Method());

  BaseObj base3;

  log("BaseObj obj_len_ = %d", base3.obj_len_);
  log("derived b3->obj_len_ = %d", b3->obj_len_);  // derived length
  log("sizeof(d3) = %d", sizeof(d3));

  unsigned char* c3 = reinterpret_cast<unsigned char*>(b3);
  log("c3[0] = %x", c3[0]);
  log("c3[1] = %x", c3[1]);
  log("c3[2] = %x", c3[2]);
  log("c3[8] = %x", c3[8]);  // this is the Obj header

  log("c3[12] = %x", c3[12]);  // this is padding?   gah.

  log("c3[16] = %x", c3[16]);  // 0xfe is member_
  log("c3[20] = %x", c3[20]);  // 0xfd is derived_member_

  // Note: if static casting, then it doesn't include the vtable pointer!  Must
  // reinterpret_cast!
  Obj* obj = reinterpret_cast<Obj*>(b3);

  ShowObj(obj);
  if ((obj->heap_tag_ & 0x1) == 0) {  // vtable pointer, NOT A TAG!
    Obj* header =
        reinterpret_cast<Obj*>(reinterpret_cast<char*>(obj) + sizeof(void*));
    // Now we have the right GC info.
    ShowObj(header);

    ASSERT_EQ_FMT(Tag::Opaque, header->heap_tag_, "%d");
    ASSERT_EQ_FMT(0, header->field_mask_, "%d");
    // casts get rid of warning
    ASSERT_EQ_FMT((int)sizeof(DerivedObj), (int)header->obj_len_, "%d");
  } else {
    ASSERT(false);  // shouldn't get here
  }

  PASS();
}

TEST inheritance_test() {
  gHeap.Init(kInitialSize);  // reset the whole thing

  ASSERT_NUM_LIVE_OBJS(0);

  DerivedObj* obj = nullptr;
  StackRoots _roots({&obj});

  ASSERT_NUM_LIVE_OBJS(0);
  gHeap.Collect();
  ASSERT_NUM_LIVE_OBJS(0);

  obj = Alloc<DerivedObj>();
  ASSERT_EQ_FMT(253, obj->derived_member_, "%d");
  ASSERT_NUM_LIVE_OBJS(1);

  gHeap.Collect();
  ASSERT_NUM_LIVE_OBJS(1);
  ASSERT_EQ_FMT(253, obj->derived_member_, "%d");

  PASS();
}

TEST protect_test() {
  Space from;
  from.Init(512);

#ifdef GC_PROTECT
  from.Protect();
  // This crashes
  // log("begin = %x", *from.begin_);
  from.Unprotect();
  ASSERT_EQ_FMT(0, *from.begin_, "%d");
#endif

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init(kInitialSize);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(test_str_creation);

  RUN_TEST(sizeof_test);
  RUN_TEST(roundup_test);
  RUN_TEST(str_test);
  RUN_TEST(list_test);
  RUN_TEST(list_repro);

  RUN_TEST(global_list_test);
  RUN_TEST(dict_test);
  RUN_TEST(dict_repro);

  RUN_TEST(fixed_trace_test);
  RUN_TEST(slab_trace_test);
  RUN_TEST(global_trace_test);

#if 0
  RUN_TEST(local_variance_test);
  RUN_TEST(local_test);
#endif

  RUN_TEST(stack_roots_test);
  RUN_TEST(field_mask_test);

  RUN_TEST(compile_time_masks_test);
  RUN_TEST(vtable_test);
  RUN_TEST(inheritance_test);
  RUN_TEST(protect_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
