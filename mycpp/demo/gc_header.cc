#include <new>  // placement new

#include "mycpp/common.h"  // for log()
#include "vendor/greatest.h"

namespace demo {

// This is 8 bytes!  Unions and bitfields don't work together?
struct Second {
  unsigned heap_tag : 2;

  union Trace {
    // Note: the string length is NOT used by the GC, so it doesn't really have
    // to be here.  But this makes the Str object smaller.

    unsigned str_len : 30;       // Tag::Opaque
    unsigned num_pointers : 30;  // Tag::Scanned
    unsigned field_mask : 30;    // Tag::Fixed
  } trace;
};

enum Tag {
  Global = 0,
  Opaque = 1,
  FixedSize = 2,
  Scanned = 3,
};

// TODO: Put this in ./configure
bool IsLittleEndian() {
  int i = 42;
  int* pointer_i = &i;
  char c = *(reinterpret_cast<char*>(pointer_i));

  // Should be 42 on little endian, 0 on big endian
  return c == 42;
}

// #define LITTLE_ENDIAN 1

class Obj {
 public:
  Obj() {
  }
  Obj(int heap_tag, int u_mask_npointers_strlen)
      : type_tag(1),  // should be odd numbers?
        heap_tag(heap_tag),
        u_mask_npointers_strlen(u_mask_npointers_strlen) {
  }

#if LITTLE_ENDIAN

  // First 32 bits
  unsigned type_tag : 8;  // for ASDL: max of 128 variants in a sum type
                          // Not 256 because it includes the NOT VTABLE bit

  // note: had small_str here, but I don't think it's feasible

  // NOTE: for Cheney, the field mask can be stored in obj_id.  Cheney needs
  // BOTH the obj_len and the field mask.  num_pointers and str_len can be
  // derived from obj_len, but field mask can't.
  //
  // Shouldn't be str_len because strings greater than 16 MiB should be
  // supported.

  unsigned obj_id : 24;  // implies 16 Mi unique objects
#else
  // Big endian version.  TODO: Put tests in mycpp/portability_test.

  unsigned obj_id : 24;
  unsigned type_tag : 8;
#endif

  // Second 32 bits
  unsigned heap_tag : 2;

  // a "union", because struct bitfields and union bitfield don't pack well
  // For Cheney, this is OBJECT length
  unsigned u_mask_npointers_strlen : 30;
};

#define FIELD_MASK(obj) (obj).u_mask_npointers_strlen
#define NUM_POINTERS(obj) (obj).u_mask_npointers_strlen
#define STR_LEN(obj) (obj).u_mask_npointers_strlen

#ifdef MARK_SWEEP
  // mark-sweep throws away obj_len
  #define WITH_HEADER(tag, field_mask, obj_len) Obj(tag, field_mask)

// Str header: STRLEN in u_mask_npointers_strlen
// Slab header: NPOINTERS in u_mask_npointers_strlen

#else
  // Cheney uses obj_len
  #define WITH_HEADER(tag, field_mask, obj_len) Obj(tag, field_mask, obj_len)

  // Store obj_len in 30-bit field (1 Gi strings)
  #define OBJ_LEN(obj) (obj).u_mask_npointers_strlen
  // Store field_mask in 24-bit field (~24 fields with inheritance)
  #define FIELD_MASK(obj) (obj).obj_id

// Str header: OBJLEN u_mask_npointers_strlen, deriving STRLEN
// Slab header: OBJLEN length in u_mask_npointers_strlen, deriving NPOINTERS
#endif

TEST gc_header_test() {
  Obj obj;
  // log("sizeof(Introspect) = %d", sizeof(Introspect));
  log("sizeof(Obj) = %d", sizeof(Obj));
  log("sizeof(Second) = %d", sizeof(Second));

  static_assert(sizeof(Obj) == 8);

  obj.type_tag = 255;
  log("type tag %d", obj.type_tag);

  obj.heap_tag = Tag::Scanned;
  log("heap tag %d", obj.heap_tag);
  obj.heap_tag = 4;  // Overflow
  log("heap tag %d", obj.heap_tag);

  FIELD_MASK(obj) = 0b11;
  log("field mask %d", FIELD_MASK(obj));
  log("num pointers %d", NUM_POINTERS(obj));
  log("str len %d", STR_LEN(obj));

#if 0
  obj.trace.str_len = 1 << 29;
  log("%d", obj.trace.str_len);
  log("%d", obj.trace.num_pointers);
  log("%d", obj.trace.field_mask);
#endif

  PASS();
}

class Node : public Obj {
 public:
  Node() : WITH_HEADER(Tag::FixedSize, 0xff, sizeof(Node)) {
  }

  virtual int Method() {
    return 42;
  }
};

class Derived : public Node {
 public:
  Derived() : Node() {
  }
  virtual int Method() {
    return 43;
  }
};

class NoVirtual : public Obj {
 public:
  NoVirtual() : WITH_HEADER(Tag::FixedSize, 0xff, sizeof(NoVirtual)) {
  }
  int i;
};

// TODO: Put this in mycpp/portability_test.cc and distribute to users

TEST endian_test() {
  log("little endian? %d", IsLittleEndian());

  Derived derived;
  log("sizeof(Node) = %d", sizeof(Node));
  log("sizeof(Derived) = %d", sizeof(Derived));

  Obj* obj = reinterpret_cast<Obj*>(&derived);
  log("Derived is GC object? %d", obj->type_tag & 0x1);

  NoVirtual n2;
  Obj* obj2 = reinterpret_cast<Obj*>(&n2);
  log("NoVirtual is GC object? %d", obj2->type_tag & 0x1);

  PASS();
}

// #if MARK_SWEEP -> change to #if CHENEY_SEMI
// #if BUMP_LEAK

TEST dual_header_test() {
  auto* n = new Node();
  log("n = %p", n);
  log("n->heap_tag %d", n->heap_tag);
  log("FIELD_MASK(*n) %d", FIELD_MASK(*n));

  PASS();
}

struct Str {
#if LITTLE_ENDIAN
  unsigned is_small : 1;  // reserved
  unsigned pad : 3;
  unsigned small_len : 4;  // 0 to 7 bytes -- not it's NOT aligned

  char small_data[7];
#else

  // TODO: How to order for big endian

#endif
};

class HeapStr : public Obj {
 public:
  // HeapStr() : Obj(Tag::Opaque, kZeroMask, kNoObjLen) {
  HeapStr() : Obj() {
  }
  char data_[1];
};

HeapStr* NewHeapStr(int n) {
  void* place = malloc(sizeof(Obj) + n + 1);  // +1 for NUL terminator
  return new (place) HeapStr();
}

// Do I want
//   typedef uintptr_t Str;
// ?
//
// No because on 32-bit I still want to store 6 string data bytes, not 2?
//
// What about
//   typedef uint64_t Str;
// ?
//
// Does that lose type safety?  Then you could accidentally type len(42) problem

typedef uint64_t MyStr;

// This is bad!
#if 0
int len(MyStr s) {
  return s;
}
#endif

// Do not initialize directly
union SmallOrBig {
  uint64_t zero_init;  // in case sizeof(HeapStr*) == 4, not 8

  Str small;  // 8 bytes
  // What if the pointer is 32 bits?  Assigning to this doesn't assign all 64
  // bits
  HeapStr* big;
};

Str StrFromHeapStr(HeapStr* p) {
  SmallOrBig result = {.zero_init = 0};
  result.big = p;
  return result.small;
}

Str SmallStrFromC(const char* s, int n) {
  Str result;
  result.is_small = 1;
  result.pad = 0;

  assert(n <= 6);  // 6 bytes
  result.small_len = n;
  memcpy(result.small_data, s, n + 1);  // copy NUL terminator too

  return result;
}

Str SmallStrFromC(const char* s) {
  return SmallStrFromC(s, strlen(s));
}

Str StrFromC_(const char* s, int n) {
  if (n <= 6) {
    return SmallStrFromC(s, n);
  } else {
    HeapStr* big = NewHeapStr(n);
    memcpy(big->data_, s, n + 1);  // copy NUL terminator too
    return StrFromHeapStr(big);
  }
}

Str StrFromC_(const char* s) {
  return StrFromC_(s, strlen(s));
}

char* StrToC(Str s) {
  if (s.is_small) {
    // log("-- is small");

    // I can't just return &(s.data[0]) ?
    char* result = &(s.small_data[0]);
    // log("result %p", result);
    return result;
  } else {
    SmallOrBig tmp = {.small = s};
    return tmp.big->data_;
  }
}

int len(Str s) {
  if (s.is_small) {
    return s.small_len;
  } else {
    SmallOrBig tmp = {.small = s};
    return strlen(tmp.big->data_);
  }
}

Str Str_upper(Str s) {
  if (s.is_small) {
    // Mutate
    for (int i = 0; i < s.small_len; ++i) {
      s.small_data[i] = toupper(s.small_data[i]);
    }
    return s;  // return a copy BY VALUE
  } else {
    SmallOrBig tmp = {.small = s};
    HeapStr* big = tmp.big;

    int n = strlen(big->data_);
    HeapStr* result = NewHeapStr(n);

    for (int i = 0; i < n; ++i) {
      result->data_[i] = toupper(big->data_[i]);
    }
    return StrFromHeapStr(result);
  }
}

#define G_SMALL_STR(name, s, small_len) Str name = {1, 0, small_len, s};

G_SMALL_STR(gSmall, "global", 6);

static_assert(sizeof(Str) == 8);

TEST small_str_test() {
  log("sizeof(Str) = %d", sizeof(Str));

  log("");
  log("---- SmallStrFromC() / StrFromC() / global G_SMALL_STR() ---- ");
  log("");

  // Str s { 1, 0, 3, "foo" };
  Str local_small = SmallStrFromC("small");
  ASSERT(local_small.is_small);
  log("local_small %s", local_small.small_data);

  Str local_s = StrFromC_("little");
  ASSERT(local_s.is_small);
  log("local_s = %s", local_s.small_data);

  log("gSmall = %s", gSmall.small_data);

  Str local_big = StrFromC_("big long string");
  ASSERT(!local_big.is_small);
  SmallOrBig either2 = {.small = local_big};

  log("either.big.data_ = %s", either2.big->data_);

  log("");
  log("---- StrToC() ---- ");
  log("");

  log("local_small = %s %d", StrToC(local_small), len(local_small));
  log("gSmall = %s %d", StrToC(gSmall), len(gSmall));
  log("local_big = %s %d", StrToC(local_big), len(local_big));

  log("");
  log("---- Str_upper() ---- ");
  log("");

  Str u1 = Str_upper(local_small);
  ASSERT(u1.is_small);

  Str u2 = Str_upper(gSmall);
  ASSERT(u2.is_small);

  Str u3 = Str_upper(local_big);
  ASSERT(!u3.is_small);

  log("local_small = %s %d", StrToC(u1), len(u1));
  log("gSmall = %s %d", StrToC(u2), len(u2));
  log("local_big = %s %d", StrToC(u3), len(u3));

  // Str toobig = SmallStrFromC("toolong");

  HeapStr* h = new HeapStr();

  SmallOrBig either;
  either.big = h;
  ASSERT(!either.small.is_small);

#if 0
  // I don't want typedef uint64_t Str because I want more type safety than
  // this !!!
  log("len(42) = %d", len(42));
#endif

  PASS();
}

}  // namespace demo

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  // gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(demo::gc_header_test);
  RUN_TEST(demo::endian_test);
  RUN_TEST(demo::dual_header_test);
  RUN_TEST(demo::small_str_test);

  // gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
