#include "mycpp/runtime.h"
#include "vendor/greatest.h"

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

enum HeapTag {
  _Global = 0,
  _Opaque = 1,
  _FixedSize = 2,
  _Scanned = 3,
};

// TODO: Put this in ./configure
bool IsLittleEndian() {
  int i = 42;
  int* pointer_i = &i;
  char c = *(reinterpret_cast<char*>(pointer_i));

  // Should be 42 on little endian, 0 on big endian
  return c == 42;
}

class Object {
 public:
  Object() {
  }
  Object(int heap_tag, int u_mask_npointers_strlen)
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
  #define WITH_HEADER(tag, field_mask, obj_len) Object(tag, field_mask)

// Str header: STRLEN in u_mask_npointers_strlen
// Slab header: NPOINTERS in u_mask_npointers_strlen

#else
  // Cheney uses obj_len
  #define WITH_HEADER(tag, field_mask, obj_len) Object(tag, field_mask, obj_len)

  // Store obj_len in 30-bit field (1 Gi strings)
  #define OBJ_LEN(obj) (obj).u_mask_npointers_strlen
  // Store field_mask in 24-bit field (~24 fields with inheritance)
  #define FIELD_MASK(obj) (obj).obj_id

// Str header: OBJLEN u_mask_npointers_strlen, deriving STRLEN
// Slab header: OBJLEN length in u_mask_npointers_strlen, deriving NPOINTERS
#endif

// SmallStr is probably not feasible.  If it is, it would greatly complicate
// the code.  It would create a branch in every function that deals with
// strings.

struct SmallStr {
  unsigned not_vtable : 1;  // 1 (true) if it's an object header, 0 (false) if
                            // it's a vtable pointer
  unsigned small_str : 1;   // reserved
  unsigned pad : 2;
  unsigned str_len : 4;  // 0 to 7 bytes -- not it's NOT aligned

  uint8_t data[7];
};

union ObjectOrStr {
  Object* obj;
  SmallStr str;
};

TEST gc_header_test() {
  Object obj;
  // log("sizeof(Introspect) = %d", sizeof(Introspect));
  log("sizeof(Object) = %d", sizeof(Object));
  log("sizeof(Second) = %d", sizeof(Second));

  static_assert(sizeof(Object) == 8);

  obj.type_tag = 255;
  log("type tag %d", obj.type_tag);

  obj.heap_tag = HeapTag::_Scanned;
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

class Node : public Object {
 public:
  Node() : WITH_HEADER(HeapTag::_FixedSize, 0xff, sizeof(Node)) {
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

class NoVirtual : public Object {
 public:
  NoVirtual() : WITH_HEADER(HeapTag::_FixedSize, 0xff, sizeof(NoVirtual)) {
  }
  int i;
};

// TODO: Put this in mycpp/portability_test.cc and distribute to users

TEST endian_test() {
  // Problem on big endian: is the high bit of a pointer necessarily 0?
  // Here this is true

  log("little endian? %d", IsLittleEndian());

  Derived derived;
  log("sizeof(Node) = %d", sizeof(Node));
  log("sizeof(Derived) = %d", sizeof(Derived));

  Object* obj = reinterpret_cast<Object*>(&derived);
  log("Derived is GC object? %d", obj->type_tag & 0x1);

  NoVirtual n2;
  Object* obj2 = reinterpret_cast<Object*>(&n2);
  log("NoVirtual is GC object? %d", obj2->type_tag & 0x1);

  PASS();
}

// #if MARK_SWEEP -> change to #if CHENEY_SEMI
// #if BUMP_LEAK

TEST dual_header_test() {
  auto* n = Alloc<Node>();
  log("n = %p", n);
  log("n->heap_tag %d", n->heap_tag);
  log("FIELD_MASK(*n) %d", FIELD_MASK(*n));

  PASS();
}

TEST small_str_test() {
  log("sizeof(SmallStr) = %d", sizeof(SmallStr));
  log("sizeof(ObjectOrStr) = %d", sizeof(ObjectOrStr));

  Object o;
  SmallStr s;

  ObjectOrStr x;
  x.obj = &o;
  log("x %p", x);

  x.str = s;
  log("x %p", x);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  // gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(gc_header_test);
  RUN_TEST(endian_test);
  RUN_TEST(dual_header_test);
  RUN_TEST(small_str_test);

  // gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
