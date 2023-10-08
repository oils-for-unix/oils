// mycpp/gc_heap_test.cc

#include "mycpp/runtime.h"
#include "vendor/greatest.h"

#define ASSERT_NUM_LIVE_OBJS(x) \
  ASSERT_EQ_FMT((x), static_cast<int>(gHeap.num_live()), "%d");

// Hm we're getting a warning because these aren't plain old data?
// https://stackoverflow.com/questions/1129894/why-cant-you-use-offsetof-on-non-pod-structures-in-c
// https://stackoverflow.com/questions/53850100/warning-offset-of-on-non-standard-layout-type-derivedclass

// The structures must be layout compatible!  Protect against typos.

#define ASSERT_GLOBAL_STR(field)                                       \
  static_assert(offsetof(Str, field) == offsetof(GlobalStr<1>, field), \
                "Str and GlobalStr should be consistent");
ASSERT_GLOBAL_STR(len_);
// NOTE: offsetof doesn't work with bitfields...
// ASSERT_GLOBAL_STR(hash_);
// ASSERT_GLOBAL_STR(is_hashed_);
ASSERT_GLOBAL_STR(data_);

static_assert(offsetof(Slab<int>, items_) ==
                  offsetof(GlobalSlab<int COMMA 1>, items_),
              "Slab and GlobalSlab should be consistent");

#define ASSERT_GLOBAL_LIST(field)                                             \
  static_assert(                                                              \
      offsetof(List<int>, field) == offsetof(GlobalList<int COMMA 1>, field), \
      "List and GlobalList should be consistent");

ASSERT_GLOBAL_LIST(len_);
ASSERT_GLOBAL_LIST(capacity_);
ASSERT_GLOBAL_LIST(slab_);

#define ASSERT_GLOBAL_DICT(field)                                       \
  static_assert(offsetof(Dict<int COMMA int>, field) ==                 \
                    offsetof(GlobalDict<int COMMA int COMMA 1>, field), \
                "Dict and GlobalDict should be consistent");

ASSERT_GLOBAL_DICT(len_);
ASSERT_GLOBAL_DICT(capacity_);
ASSERT_GLOBAL_DICT(index_);
ASSERT_GLOBAL_DICT(keys_);
ASSERT_GLOBAL_DICT(values_);

void ShowSlab(void* obj) {
  auto slab = reinterpret_cast<Slab<void*>*>(obj);
  auto* header = ObjHeader::FromObject(obj);
  assert(header->heap_tag == HeapTag::Scanned);

  int n = NUM_POINTERS(*header);
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
TEST field_masks_test() {
  auto L = NewList<int>();
  StackRoots _roots({&L});

  L->append(1);
  log("List mask = %d", FIELD_MASK(*ObjHeader::FromObject(L)));

  auto d = Alloc<Dict<Str*, int>>();
  StackRoots _roots2({&d});

  auto key = StrFromC("foo");
  StackRoots _roots9({&key});
  d->set(key, 3);

  // oops this is bad?  Because StrFromC() might move d in the middle of the
  // expression!  Gah!
  // d->set(StrFromC("foo"), 3);

  log("Dict mask = %d", FIELD_MASK(*ObjHeader::FromObject(d)));

#if 0
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

TEST offsets_test() {
  // Note: These will be different for 32 bit

  ASSERT_EQ(offsetof(List<int>, slab_),
            offsetof(GlobalList<int COMMA 1>, slab_));

  if (sizeof(void*) == 8) {
    // 0b 0000 0010
    unsigned list_mask = List<int>::field_mask();
    ASSERT_EQ_FMT(0x0002, list_mask, "0x%x");

    // in binary: 0b 0000 0000 0001 1100
    unsigned dict_mask = Dict<int COMMA int>::field_mask();
    ASSERT_EQ_FMT(0x0001c, dict_mask, "0x%x");
  }

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

TEST list_resize_policy_test() {
  log("int kNumItems2 %d", List<int>::kNumItems2);
  log("Str* kNumItems2 %d", List<Str*>::kNumItems2);

  log("");
  log("\tList<int>");

  auto small = NewList<int>();

  for (int i = 0; i < 20; ++i) {
    small->append(i);
    int c = small->capacity_;
    log("i %d capacity %d alloc %d", i, c, 8 + c * sizeof(int));
  }

  log("");
  log("\tList<Str*>");

  // Note: on 32-bit systems, this should be the same

  auto big = NewList<Str*>();
  for (int i = 0; i < 20; ++i) {
    big->append(kEmptyString);
    int c = big->capacity_;
    log("i %d capacity %d alloc %d", i, c, 8 + c * sizeof(Str*));
  }

  PASS();
}

TEST dict_resize_policy_test() {
  log("Dict min items %d", Dict<int, int>::kMinItems);
  log("kHeaderFudge %d", Dict<int, int>::kHeaderFudge);
  log("--");

  auto small = Alloc<Dict<int, int>>();

  for (int i = 0; i < 20; ++i) {
    small->set(i, i);
    int c = small->capacity_;
    log("i %d capacity %d alloc %d", i, c, 8 + c * sizeof(int));
  }

  PASS();
}

class Point {
 public:
  Point(int x, int y) : x_(x), y_(y) {
  }
  int size() {
    return x_ + y_;
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(kZeroMask, sizeof(Point));
  }

  int x_;
  int y_;
};

const int kLineMask = 0x3;  // 0b0011

class Line {
 public:
  Line() : begin_(nullptr), end_(nullptr) {
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(kLineMask, sizeof(Line));
  }

  Point* begin_;
  Point* end_;
};

TEST fixed_trace_test() {
  gHeap.Collect();

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

GLOBAL_STR(str4, "egg");

TEST slab_trace_test() {
  gHeap.Collect();

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
  gHeap.Collect();

  Str* l4 = nullptr;
  List<Str*>* strings = nullptr;

  int num_roots;
  num_roots = gHeap.roots_.size();
  ASSERT_EQ_FMT(0, num_roots, "%d");

  StackRoots _roots({&l4, &strings});

  num_roots = gHeap.roots_.size();
  ASSERT_EQ_FMT(2, num_roots, "%d");

  // 2 roots, but no live objects
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

// 8 byte vtable, 8 byte ObjHeader, then member_
class BaseObj {
 public:
  explicit BaseObj(uint32_t obj_len) {
  }
  BaseObj() : BaseObj(sizeof(BaseObj)) {
  }

  virtual int Method() {
    return 3;
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(kZeroMask, sizeof(BaseObj));
  }

  int member_ = 254;
};

// 8 byte vtable, 8 byte ObjHeader, then member_, then derived_member_
class DerivedObj : public BaseObj {
 public:
  DerivedObj() : BaseObj(sizeof(DerivedObj)) {
  }
  virtual int Method() {
    return 4;
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(kZeroMask, sizeof(DerivedObj));
  }

  int derived_member_ = 253;
  int derived_member2_ = 252;
};

void ShowObj(ObjHeader* obj) {
  log("obj->heap_tag %d", obj->heap_tag);
#if 0
  log("obj->obj_len %d", obj->obj_len);
#endif
}

TEST inheritance_test() {
  gHeap.Collect();

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

TEST stack_roots_test() {
  Str* s = nullptr;
  List<int>* L = nullptr;

  gHeap.Collect();

  ASSERT_EQ(0, gHeap.roots_.size());

  StackRoots _roots({&s, &L});

  s = StrFromC("foo");
  L = NewList<int>();

  int num_roots = gHeap.roots_.size();
  ASSERT_EQ_FMT(2, num_roots, "%u");

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(field_masks_test);
  RUN_TEST(offsets_test);

  RUN_TEST(roundup_test);
  RUN_TEST(list_resize_policy_test);
  RUN_TEST(dict_resize_policy_test);

  RUN_TEST(fixed_trace_test);
  RUN_TEST(slab_trace_test);
  RUN_TEST(global_trace_test);

  RUN_TEST(inheritance_test);

  RUN_TEST(stack_roots_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
