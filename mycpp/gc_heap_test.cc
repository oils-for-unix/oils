// Unit tests for gc_heap

// More tests to do:
//
// - Integrate with ASDL and use the pretty printer.
//
// - Integrate with mycpp and run mycpp/examples/
//   - Make sure the benchmarks show less heap usage.

#include "gc_heap.h"
#include "greatest.h"

// Types
using gc_heap::Heap;
using gc_heap::Local;
using gc_heap::Obj;

using gc_heap::Dict;
using gc_heap::GlobalStr;
using gc_heap::List;
using gc_heap::NewStr;
using gc_heap::Slab;
using gc_heap::Str;

// Constants
using gc_heap::kSlabHeaderSize;
using gc_heap::kStrHeaderSize;
using gc_heap::kZeroMask;

// Functions
using gc_heap::Alloc;
using gc_heap::RoundUp;

// Variables
using gc_heap::gHeap;

// 1 MiB, and will double when necessary.  Note: femtolisp uses 512 KiB.
const int kInitialSize = 1 << 20;

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

constexpr int n4 = 3;
GlobalStr<n4 + 1> g4 = {
    Tag::Opaque,      0,    kZeroMask, kStrHeaderSize + n4 + 1, n4,
    .unique_id_ = -1, "egg"};

Str* g5 = reinterpret_cast<Str*>(&g4);

TEST str_test() {
  auto str1 = NewStr("");
  auto str2 = NewStr("one\0two", 7);

  ASSERT_EQ_FMT(Tag::Opaque, str1->heap_tag, "%d");
  ASSERT_EQ_FMT(kStrHeaderSize + 1, str1->obj_len_, "%d");
  ASSERT_EQ_FMT(kStrHeaderSize + 7 + 1, str2->obj_len_, "%d");

  // Make sure they're on the heap
  int diff1 = reinterpret_cast<char*>(str1) - gHeap.from_space_;
  int diff2 = reinterpret_cast<char*>(str2) - gHeap.from_space_;
  ASSERT(diff1 < 1024);
  ASSERT(diff2 < 1024);

  ASSERT_EQ(0, len(str1));
  ASSERT_EQ(7, len(str2));

  // Make sure it's directly contained
  ASSERT_EQ('e', g4.data_[0]);
  ASSERT_EQ('g', g4.data_[1]);
  ASSERT_EQ('g', g4.data_[2]);
  ASSERT_EQ('\0', g4.data_[3]);

  ASSERT_EQ('e', g5->data_[0]);
  ASSERT_EQ(Tag::Opaque, g5->heap_tag);
  ASSERT_EQ(20, g5->obj_len_);
  ASSERT_EQ(3, len(g5));

  PASS();
}

// TODO:
//
// - Test what happens append() runs over the max heap size
//   - how does it trigger a collection?

TEST list_test() {
  auto list1 = Alloc<List<int>>();
  auto list2 = Alloc<List<Str*>>();

  ASSERT_EQ(0, len(list1));
  ASSERT_EQ(0, len(list2));

  ASSERT_EQ_FMT(0, list1->capacity_, "%d");
  ASSERT_EQ_FMT(0, list2->capacity_, "%d");

  ASSERT_EQ_FMT(Tag::FixedSize, list1->heap_tag, "%d");
  ASSERT_EQ_FMT(Tag::FixedSize, list2->heap_tag, "%d");

  // 8 byte obj header + 2 integers + pointer
  ASSERT_EQ_FMT(24, list1->obj_len_, "%d");
  ASSERT_EQ_FMT(24, list2->obj_len_, "%d");

  // Make sure they're on the heap
  int diff1 = reinterpret_cast<char*>(list1) - gHeap.from_space_;
  int diff2 = reinterpret_cast<char*>(list2) - gHeap.from_space_;
  ASSERT(diff1 < 1024);
  ASSERT(diff2 < 1024);

  list1->extend({11, 22, 33});
  ASSERT_EQ_FMT(3, len(list1), "%d");

  // 32 byte block - 8 byte header = 24 bytes, 6 elements
  ASSERT_EQ_FMT(6, list1->capacity_, "%d");
  ASSERT_EQ_FMT(Tag::Opaque, list1->slab_->heap_tag, "%d");

  // 8 byte header + 3*4 == 8 + 12 == 20, rounded up to power of 2
  ASSERT_EQ_FMT(32, list1->slab_->obj_len_, "%d");

  ASSERT_EQ_FMT(11, list1->index(0), "%d");
  ASSERT_EQ_FMT(22, list1->index(1), "%d");
  ASSERT_EQ_FMT(33, list1->index(2), "%d");

  log("extending");
  list1->extend({44, 55, 66, 77});

  // 64 byte block - 8 byte header = 56 bytes, 14 elements
  ASSERT_EQ_FMT(14, list1->capacity_, "%d");
  ASSERT_EQ_FMT(7, len(list1), "%d");

  // 8 bytes header + 7*4 == 8 + 28 == 36, rounded up to power of 2
  ASSERT_EQ_FMT(64, list1->slab_->obj_len_, "%d");

  ASSERT_EQ_FMT(11, list1->index(0), "%d");
  ASSERT_EQ_FMT(22, list1->index(1), "%d");
  ASSERT_EQ_FMT(33, list1->index(2), "%d");
  ASSERT_EQ_FMT(44, list1->index(3), "%d");
  ASSERT_EQ_FMT(55, list1->index(4), "%d");
  ASSERT_EQ_FMT(66, list1->index(5), "%d");
  ASSERT_EQ_FMT(77, list1->index(6), "%d");

  list1->append(88);
  ASSERT_EQ_FMT(88, list1->index(7), "%d");
  ASSERT_EQ_FMT(8, len(list1), "%d");

  int d_slab = reinterpret_cast<char*>(list1->slab_) - gHeap.from_space_;
  ASSERT(d_slab < 1024);

  log("list1_ = %p", list1);
  log("list1->slab_ = %p", list1->slab_);

  auto str1 = NewStr("foo");
  log("str1 = %p", str1);
  auto str2 = NewStr("bar");
  log("str2 = %p", str2);

  list2->append(str1);
  list2->append(str2);
  ASSERT_EQ(2, len(list2));
  ASSERT_EQ(str1, list2->index(0));
  ASSERT_EQ(str2, list2->index(1));

  // This combination is problematic.  Maybe avoid it and then just do
  // .extend({1, 2, 3}) or something?
  // https://stackoverflow.com/questions/21573808/using-initializer-lists-with-variadic-templates
  // auto list3 = Alloc<List<int>>({1, 2, 3});
  // auto list4 = Alloc<List<Str*>>({str1, str2});

  // log("len(list3) = %d", len(list3));
  // log("len(list4) = %d", len(list3));

  PASS();
}

// TODO:
// - Test set() can resize the dict
//   - I guess you have to do rehashing?

TEST dict_test() {
  auto dict1 = Alloc<Dict<int, int>>();
  auto dict2 = Alloc<Dict<Str*, Str*>>();

  ASSERT_EQ(0, len(dict1));
  ASSERT_EQ(0, len(dict2));

  ASSERT_EQ_FMT(Tag::FixedSize, dict1->heap_tag, "%d");
  ASSERT_EQ_FMT(Tag::FixedSize, dict1->heap_tag, "%d");

  ASSERT_EQ_FMT(0, dict1->capacity_, "%d");
  ASSERT_EQ_FMT(0, dict2->capacity_, "%d");

  ASSERT_EQ(nullptr, dict1->index_);
  ASSERT_EQ(nullptr, dict1->keys_);
  ASSERT_EQ(nullptr, dict1->values_);

  // Make sure they're on the heap
  int diff1 = reinterpret_cast<char*>(dict1) - gHeap.from_space_;
  int diff2 = reinterpret_cast<char*>(dict2) - gHeap.from_space_;
  ASSERT(diff1 < 1024);
  ASSERT(diff2 < 1024);

  dict1->set(42, 5);
  ASSERT_EQ(5, dict1->index(42));
  ASSERT_EQ(1, len(dict1));
  ASSERT_EQ_FMT(6, dict1->capacity_, "%d");

  ASSERT_EQ_FMT(32, dict1->index_->obj_len_, "%d");
  ASSERT_EQ_FMT(32, dict1->keys_->obj_len_, "%d");
  ASSERT_EQ_FMT(32, dict1->values_->obj_len_, "%d");

  dict1->set(42, 99);
  ASSERT_EQ(99, dict1->index(42));
  ASSERT_EQ(1, len(dict1));
  ASSERT_EQ_FMT(6, dict1->capacity_, "%d");

  dict1->set(43, 10);
  ASSERT_EQ(10, dict1->index(43));
  ASSERT_EQ(2, len(dict1));
  ASSERT_EQ_FMT(6, dict1->capacity_, "%d");

  for (int i = 0; i < 14; ++i) {
    dict1->set(i, 999);
    log("i = %d, capacity = %d", i, dict1->capacity_);

    // make sure we didn't lose old entry after resize
    ASSERT_EQ(10, dict1->index(43));
  }

  dict2->set(NewStr("foo"), NewStr("bar"));
  ASSERT_EQ(1, len(dict2));
  ASSERT(str_equals(NewStr("bar"), dict2->index(NewStr("foo"))));

  ASSERT_EQ_FMT(32, dict2->index_->obj_len_, "%d");
  ASSERT_EQ_FMT(64, dict2->keys_->obj_len_, "%d");
  ASSERT_EQ_FMT(64, dict2->values_->obj_len_, "%d");

  // Check other sizes

  auto dict_si = Alloc<Dict<Str*, int>>();
  dict_si->set(NewStr("foo"), 42);
  ASSERT_EQ(1, len(dict_si));

  ASSERT_EQ_FMT(32, dict_si->index_->obj_len_, "%d");
  ASSERT_EQ_FMT(64, dict_si->keys_->obj_len_, "%d");
  ASSERT_EQ_FMT(32, dict_si->values_->obj_len_, "%d");

  auto dict_is = Alloc<Dict<int, Str*>>();
  dict_is->set(42, NewStr("foo"));
  ASSERT_EQ(1, len(dict_is));

  ASSERT_EQ_FMT(32, dict_is->index_->obj_len_, "%d");
  ASSERT_EQ_FMT(32, dict_is->keys_->obj_len_, "%d");
  ASSERT_EQ_FMT(64, dict_is->values_->obj_len_, "%d");

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

  ASSERT_EQ_FMT(0, gHeap.num_live_objs_, "%d");

  // auto p = Local<Point>(Alloc<Point>(3, 4));
  Local<Point> p = Alloc<Point>(3, 4);
  log("point size = %d", p->size());

  ASSERT_EQ_FMT(1, gHeap.num_live_objs_, "%d");

  auto line = Local<Line>(Alloc<Line>());

  line->begin_ = p;
  line->end_ = Alloc<Point>(5, 6);

  ASSERT_EQ_FMT(3, gHeap.num_live_objs_, "%d");

  gHeap.Collect();
  ASSERT_EQ_FMT(3, gHeap.num_live_objs_, "%d");

  // remove last reference
  line->end_ = nullptr;

  gHeap.Collect();
  ASSERT_EQ_FMT(2, gHeap.num_live_objs_, "%d");

  PASS();
}

TEST slab_trace_test() {
  gHeap.Init(kInitialSize);  // reset the whole thing

  ASSERT_EQ_FMT(0, gHeap.num_live_objs_, "%d");

  {
    Local<List<int>> ints = Alloc<List<int>>();
    ASSERT_EQ_FMT(1, gHeap.num_live_objs_, "%d");

    ints->append(3);
    ASSERT_EQ_FMT(2, gHeap.num_live_objs_, "%d");
  }
  gHeap.Collect();
  ASSERT_EQ_FMT(0, gHeap.num_live_objs_, "%d");

  Local<List<Str*>> strings = Alloc<List<Str*>>();
  ASSERT_EQ_FMT(1, gHeap.num_live_objs_, "%d");

  Local<Str> s = NewStr("yo");
  strings->append(s);
  ASSERT_EQ_FMT(3, gHeap.num_live_objs_, "%d");

  strings->append(NewStr("bar"));
  ASSERT_EQ_FMT(4, gHeap.num_live_objs_, "%d");

  // remove reference
  strings->set(1, nullptr);

  gHeap.Collect();
  ASSERT_EQ_FMT(3, gHeap.num_live_objs_, "%d");

  PASS();
}

void ShowRoots(const Heap& heap) {
  log("--");
  for (int i = 0; i < heap.roots_top_; ++i) {
    log("%d. %p", i, heap.roots_[i]);
    // This is NOT on the heap; it's on the stack.
    // int diff1 = reinterpret_cast<char*>(heap.roots[i]) - gHeap.from_space_;
    // assert(diff1 < 1024);

    auto h = static_cast<Local<void>*>(heap.roots_[i]);
    auto raw = h->raw_pointer_;
    log("   %p", raw);

    // Raw pointer is on the heap.
    int diff2 = reinterpret_cast<char*>(raw) - gHeap.from_space_;
    // log("diff2 = %d", diff2);
    assert(diff2 < 2048);

    // This indeed mutates it and causes a crash
    // h->Update(nullptr);
  }
}

Str* myfunc() {
  Local<Str> str1(NewStr("foo"));
  Local<Str> str2(NewStr("foo"));
  Local<Str> str3(NewStr("foo"));

  log("myfunc roots_top = %d", gHeap.roots_top_);
  ShowRoots(gHeap);

  return str1;  // implicit conversion to raw pointer
}

void otherfunc(Local<Str> s) {
  log("otherfunc roots_top_ = %d", gHeap.roots_top_);
  log("len(s) = %d", len(s));
}

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

    Local<Str> str2(NewStr("bar"));
    ASSERT_EQ(2, gHeap.roots_top_);

    myfunc();

    otherfunc(str2);
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

  PASS();
}

void ShowSlab(Obj* obj) {
  assert(obj->heap_tag == Tag::Scanned);
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
  auto L = Alloc<List<int>>();
  L->append(1);
  log("List mask = %d", L->field_mask_);

  auto d = Alloc<Dict<Str*, int>>();
  d->set(NewStr("foo"), 3);
  log("Dict mask = %d", d->field_mask_);

  gc_heap::ShowFixedChildren(L);
  gc_heap::ShowFixedChildren(d);

  auto L2 = gc_heap::Alloc<List<Str*>>();
  auto s = NewStr("foo");
  L2->append(s);
  L2->append(s);
  ShowSlab(L2->slab_);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  // Should be done once per thread
  gHeap.Init(kInitialSize);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(sizeof_test);
  RUN_TEST(roundup_test);
  RUN_TEST(str_test);
  RUN_TEST(list_test);
  RUN_TEST(dict_test);
  RUN_TEST(fixed_trace_test);
  RUN_TEST(slab_trace_test);
  RUN_TEST(local_test);
  RUN_TEST(field_mask_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
