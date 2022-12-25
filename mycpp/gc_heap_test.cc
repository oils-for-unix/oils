// mycpp/gc_heap_test.cc

#include "mycpp/runtime.h"
#include "vendor/greatest.h"

#define ASSERT_NUM_LIVE_OBJS(x) \
  ASSERT_EQ_FMT((x), static_cast<int>(gHeap.num_live_), "%d");

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
TEST field_masks_test() {
  auto L = NewList<int>();
  StackRoots _roots({&L});

  L->append(1);
  log("List mask = %d", L->header_.field_mask_);

  auto d = Alloc<Dict<Str*, int>>();
  StackRoots _roots2({&d});

  auto key = StrFromC("foo");
  StackRoots _roots9({&key});
  d->set(key, 3);

  // oops this is bad?  Because StrFromC() might move d in the middle of the
  // expression!  Gah!
  // d->set(StrFromC("foo"), 3);

  log("Dict mask = %d", d->header_.field_mask_);

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
  // 0b 0000 0010
  unsigned list_mask = List<int>::field_mask();
  ASSERT_EQ_FMT(0x0002, list_mask, "0x%x");

  // in binary: 0b 0000 0000 0000 01110
  unsigned dict_mask = Dict<int COMMA int>::field_mask();
  ASSERT_EQ_FMT(0x000E, dict_mask, "0x%x");

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

class Point {
 public:
  Point(int x, int y)
      : GC_CLASS_FIXED(header_, kZeroMask, sizeof(Point)), x_(x), y_(y) {
  }
  int size() {
    return x_ + y_;
  }
  GC_OBJ(header_);
  int x_;
  int y_;
};

const int kLineMask = 0x3;  // 0b0011

class Line {
 public:
  Line()
      : GC_CLASS_FIXED(header_, kLineMask, sizeof(Line)),
        begin_(nullptr),
        end_(nullptr) {
  }
  GC_OBJ(header_);
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

// 8 byte vtable, 8 byte Obj header, then member_
class BaseObj {
 public:
  explicit BaseObj(int obj_len) : GC_CLASS_FIXED(header_, kZeroMask, obj_len) {
  }
  BaseObj() : BaseObj(sizeof(BaseObj)) {
  }

  virtual int Method() {
    return 3;
  }

  GC_OBJ(header_);
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

  log("BaseObj obj_len_ = %d", base3.header_.obj_len_);
  log("derived b3->obj_len_ = %d", b3->header_.obj_len_);  // derived length
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

    ASSERT_EQ_FMT(Tag::FixedSize, header->heap_tag_, "%d");
    ASSERT_EQ_FMT(0, header->field_mask_, "%d");
    // casts get rid of warning
    ASSERT_EQ_FMT((int)sizeof(DerivedObj), (int)header->obj_len_, "%d");
  } else {
    ASSERT(false);  // shouldn't get here
  }

  PASS();
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

#if 0
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
#endif

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

  RUN_TEST(fixed_trace_test);
  RUN_TEST(slab_trace_test);
  RUN_TEST(global_trace_test);

  RUN_TEST(vtable_test);
  RUN_TEST(inheritance_test);

  RUN_TEST(stack_roots_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
