#include <inttypes.h>
#include <limits.h>  // HOST_NAME_MAX
#include <string.h>  // memcpy()
#include <time.h>    // strftime()
#include <unistd.h>  // gethostname()

#include <new>  // placement new

#include "mycpp/common.h"  // for log()
#include "vendor/greatest.h"

namespace demo {

// Could put this in ./configure, although glibc seems to have it
bool IsLittleEndian() {
  int i = 42;
  int* pointer_i = &i;
  char c = *(reinterpret_cast<char*>(pointer_i));

  // Should be 42 on little endian, 0 on big endian
  return c == 42;
}

const int kIsHeader = 1;
const int kNoObjId = 0;

enum TypeTag {
  Class = 0,
  String = 1,  // note: 'Str' would conflict with 'class Str'
};

enum HeapTag {
  Global = 0,
  Opaque = 1,
  FixedSize = 2,
  Scanned = 3,

  Forwarded = 4,  // only for Cheney
};

//
// NEW OBJECT HEADER (with 24-bit object ID, also usable with Cheney collector)
//

struct ObjHeader {
  // --- First 32 bits ---

#if 1  // little endian
  // Set to 1, for the garbage collector to distinguish with vtable bits
  unsigned is_header : 1;

  // - 0 is for user-defined classes
  // - 1 to 6 reserved for "tagless" value:
  // value_e.{Str,List,Dict,Bool,Int,Float}
  // - 7 to 127: ASDL union, so we have a maximuim of ~120 variants.
  unsigned type_tag : 7;

  #if MARK_SWEEP
  unsigned obj_id : 24;  // small index into mark bitmap, implies 16 Mi unique
                         // objects
  #else
  unsigned field_mask : 24;  // Cheney doesn't need obj_id, but needs
                             // field_mask AND obj_len
  #endif

#else
  // Possible 32-bit big endian version.  TODO: Put tests in
  // mycpp/portability_test.cc
  unsigned obj_id : 24;
  unsigned is_header : 1;
  unsigned type_tag : 7;
#endif

  // --- Second 32 bits ---

#if MARK_SWEEP
  // A fake "union", because unions and bitfields don't pack as you'd like
  unsigned heap_tag : 2;  // HeapTag::Opaque, HeapTag::Scanned, etc.
  unsigned u_mask_npointers_strlen : 30;
#else
  unsigned heap_tag : 3;  // also needs HeapTag::Forwarded
  unsigned obj_len : 29;
#endif
};

#ifdef BUMP_LEAK
  // omit GC header
  #define GC_OBJ(var_name)
#else
  #define GC_OBJ(var_name) ObjHeader var_name
#endif

// ON string construction, we don't know the string length or object length
#define GC_STR(header_)                                      \
  header_ {                                                  \
    kIsHeader, TypeTag::String, kNoObjId, HeapTag::Opaque, 0 \
  }

#ifdef MARK_SWEEP
  // obj_len thrown away
  #define GC_CLASS_FIXED(header_, field_mask, obj_len)                    \
    header_ {                                                             \
      kIsHeader, TypeTag::Class, kNoObjId, HeapTag::FixedSize, field_mask \
    }
  // Used by code generators: ASDL, mycpp
  #define GC_CLASS_SCANNED(header_, num_pointers, obj_len)                \
    header_ {                                                             \
      kIsHeader, TypeTag::Class, kNoObjId, HeapTag::Scanned, num_pointers \
    }

  // Different values stored in the same "union" field
  #define FIELD_MASK(header) (header).u_mask_npointers_strlen
  #define NUM_POINTERS(header) (header).u_mask_npointers_strlen

#else

  // 24-bit object ID is used for field mask, 30-bit obj_len for copying
  #define GC_CLASS_FIXED(header_, field_mask, obj_len)                   \
    header_ {                                                            \
      kIsHeader, TypeTag::Class, field_mask, HeapTag::FixedSize, obj_len \
    }
  // num_pointers thrown away, because it can be derived
  #define GC_CLASS_SCANNED(header_, num_pointers, obj_len)            \
    header_ {                                                         \
      kIsHeader, TypeTag::Class, kZeroMask, HeapTag::Scanned, obj_len \
    }

  // Store field_mask in 24-bit field (~24 fields with inheritance)
  #define FIELD_MASK(header) (header).field_mask

  // Derive num pointers from object length
  #define NUM_POINTERS(header) \
    (((header).obj_len - sizeof(ObjHeader)) / sizeof(void*))

#endif

struct LayoutGc {
  ObjHeader header;
  uint8_t place[1];  // flexible array, for placement new
};

// Hm I guess this has to be templated.

// 4 steps:
// 1. allocate untyped data
// 2. invoke constructor
// 3. header data known statically
// 4. header data that's dynamic, like object ID

#define GC_NEW(T, ...)                                                \
  LayoutGc* untyped = gHeap.Allocate();                               \
  T* obj = new (untyped.place)(...) untyped.header = T::obj_header(); \
  untyped.header.obj_id = gHeap.mark_set_.NextObjectId() return obj

// Alloc<T> can solve the  VTABLE problem if we want
// However it can't solve the code bloat problem
// you need to be able to do "return GC_NEW()"

// We remove FindHeader etc.

class Point {
 public:
  int x;
  int y;
  static constexpr ObjHeader object_header() {
    return ObjHeader{0};
  }
};

// Replacement for crazy macro
// Problem: you can't dynamically assign object ID this way.
//
// Actually if you say the ALLOCATOR always does it ... hm.
// Because it's always in the same place?
//
// code bloat isn't that bad actually
// But yeah you want to reduce it by not having FindObjHeader() in there!!!
// I think we can do that
// ---
// And also if MarkSweepHeap is responsible for it, then you don't have as many
// code paths You don't have to check every caller of Allocate()

template <typename T>
T* Alloc() {
  // return reinterpret_cast<T*>( LayoutGc { T::object_header(), new (malloc(1))
  // T() }.place );

  // gHeap.Allocate()
  LayoutGc* untyped =
      static_cast<LayoutGc*>(malloc(sizeof(ObjHeader) + sizeof(T)));
  untyped->header = T::object_header();  // It's always before the vtable

  // gHeap.GetObjectId()
  untyped->header.obj_id = 124;  // dynamic, but ca be done by allocator
  return new (untyped->place) T();
}

TEST gc_new_test() {
  Point* p = Alloc<Point>();
  log("p = %p", p);

  PASS();
}

TEST gc_header_test() {
  ObjHeader obj;
  // log("sizeof(Introspect) = %d", sizeof(Introspect));
  log("sizeof(ObjHeader) = %d", sizeof(ObjHeader));

  static_assert(sizeof(ObjHeader) == 8, "expected 8 byte header");

  obj.type_tag = 127;
  log("type tag %d", obj.type_tag);

  obj.heap_tag = HeapTag::Scanned;
  log("heap tag %d", obj.heap_tag);

  // obj.heap_tag = 4;  // Overflow
  // log("heap tag %d", obj.heap_tag);

  PASS();
}

class Node {
 public:
  Node() : GC_CLASS_FIXED(header_, field_mask(), sizeof(Node)) {
  }

  virtual int Method() {
    return 42;
  }

  GC_OBJ(header_);

  // max is either 24 or 30 bits, so use unsigned int
  static constexpr unsigned int field_mask() {
    return 0x0f;
  }
};

class Derived : public Node {
 public:
  Derived() : Node() {
    FIELD_MASK(header_) |= Derived::field_mask();
  }

  virtual int Method() {
    return 43;
  }

  int x;

  static constexpr unsigned field_mask() {
    return 0x30;
  }
};

class NoVirtual {
 public:
  NoVirtual() : GC_CLASS_FIXED(header_, field_mask(), sizeof(NoVirtual)) {
  }

  GC_OBJ(header_);
  int i;

  static constexpr unsigned field_mask() {
    return 0xf0;
  }
};

// TODO: Put this in mycpp/portability_test.cc and distribute to users

TEST endian_test() {
  log("little endian? %d", IsLittleEndian());

  Derived derived;
  log("sizeof(Node) = %d", sizeof(Node));
  log("sizeof(Derived) = %d", sizeof(Derived));

  ObjHeader* header = reinterpret_cast<ObjHeader*>(&derived);
  log("Derived is GC object? %d", header->type_tag & 0x1);

  NoVirtual n2;
  ObjHeader* header2 = reinterpret_cast<ObjHeader*>(&n2);
  log("NoVirtual is GC object? %d", header2->type_tag & 0x1);

  auto n = new Node();
  FIELD_MASK(n->header_) = 0b11;
  log("field mask %d", FIELD_MASK(n->header_));
  log("num pointers %d", NUM_POINTERS(n->header_));

  PASS();
}

// #if MARK_SWEEP -> change to #if CHENEY_SEMI
// #if BUMP_LEAK

TEST dual_header_test() {
  auto* n = new Node();
  log("n = %p", n);
  log("n->heap_tag %d", n->header_.heap_tag);
  log("FIELD_MASK(n) %d", FIELD_MASK(n->header_));

  PASS();
}

//
// Union test
//

// This is 8 bytes!  Unions and bitfields don't work together?
struct UnionBitfield {
  unsigned heap_tag : 2;

  union Trace {
    // Note: the string length is NOT used by the GC, so it doesn't really have
    // to be here.  But this makes the Str object smaller.

    unsigned str_len : 30;       // HeapTag::Opaque
    unsigned num_pointers : 30;  // HeapTag::Scanned
    unsigned field_mask : 30;    // HeapTag::Fixed
  } trace;
};

//
// header_.is_header  // 1 bit
// header_.type_tag   // 7 bits
//
// #ifdef MARK_SWEEP
//   header_.obj_id
// #else
//   header_.field_mask
// #endif
//
// header_.heap_tag
//
// #ifdef MARK_SWEEP
//   union {
//     header_.field_mask.val
//     header_.str_len.val
//     header_.num_pointers.val
//   }
// #else
//   header_.obj_len
// #endif

union ObjHeader2 {
  // doesn't work: initializations for multiple members?
  // ObjHeader2() : raw_bytes(0), is_header(1) {

  // also doesn't work
  // ObjHeader2() : is_header(1), type_tag(1) {

  ObjHeader2() : raw_bytes(0) {
  }

  uint64_t raw_bytes;

  class _is_header {
   public:
    _is_header(int val) : val(val) {
    }
    unsigned val : 1;
    unsigned _1 : 31;
    unsigned _2 : 32;
  } is_header;

  struct _type_tag {
    _type_tag(int val) : val(val) {
    }
    unsigned _1 : 1;
    unsigned val : 7;
    unsigned _2 : 24;
    unsigned _3 : 32;
  } type_tag;

  struct _obj_id {
    unsigned _1 : 8;
    unsigned val : 24;
    unsigned _2 : 32;
  } obj_id;

  struct _heap_tag {
    unsigned _1 : 32;
    unsigned val : 2;
    unsigned _2 : 30;
  } heap_tag;

  // These three share the same bigs
  struct _field_mask {
    unsigned _1 : 32;
    unsigned _2 : 2;
    unsigned val : 30;
  } field_mask;

  struct _str_len {
    unsigned _1 : 32;
    unsigned _2 : 2;
    unsigned val : 30;
  } str_len;

  struct _num_pointers {
    unsigned _1 : 32;
    unsigned _2 : 2;
    unsigned val : 30;
  } num_pointers;

  // Hand-written classes, including fixed size List and Dict headers
  void InitFixedClass(int field_mask) {
    this->is_header.val = 1;
    this->heap_tag.val = HeapTag::FixedSize;
    this->field_mask.val = field_mask;
  }

  // - Slab<List*>, Slab<Str> (might be HeapStr*)
  // - Generated classes without inheritance
  // - all ASDL types
  void InitScanned(int num_pointers) {
    this->is_header.val = 1;
    this->heap_tag.val = HeapTag::Scanned;
    this->num_pointers.val = num_pointers;
  }

  void InitStr(int str_len) {
    this->is_header.val = 1;
    this->heap_tag.val = HeapTag::Opaque;
    this->str_len.val = str_len;
  }

  void InitAsdlVariant(int type_tag, int num_pointers) {
    this->is_header.val = 1;

    this->type_tag.val = type_tag;

    this->heap_tag.val = HeapTag::Scanned;
    this->num_pointers.val = num_pointers;
  }

  // Other:
  // - HeapTag::Global is for GlobalBigStr*, GLOBAL_LIST, ...
  //
  // All the variants of value_e get their own type tag?
  // - Boxed value.{Bool,Int,Float}
  // - And "boxless" / "tagless" Str, List, Dict
};

class Token {
 public:
  Token() : header_() {
  }

  ObjHeader2 header_;
};

TEST union_test() {
  log("sizeof(UnionBitfield) = %d", sizeof(UnionBitfield));

  Token t;

  t.header_.is_header.val = 1;

  t.header_.type_tag.val = 127;
  t.header_.obj_id.val = 12345678;  // max 16 Mi

  t.header_.heap_tag.val = HeapTag::Scanned;
  t.header_.field_mask.val = 0xff;

  log("is_header %d", t.header_.is_header.val);

  log("type_tag %d", t.header_.type_tag.val);
  log("obj_id %d", t.header_.obj_id.val);

  log("heap_tag %d", t.header_.heap_tag.val);

  log("field_mask %d", t.header_.field_mask.val);
  log("str_len %d", t.header_.str_len.val);
  log("num_pointers %d", t.header_.num_pointers.val);

  // Garbage collector

  // First check check SmallStr.is_present_ - it might not be a pointer at all
  ObjHeader2* obj = reinterpret_cast<ObjHeader2*>(&t);

  // Then check for vtable - it might not be a pointer to an ObjHeader2
  if (!obj->is_header.val) {
    // advance 8 bytes and assert header.is_header
    log("Not a header");
  }

  PASS();
}

}  // namespace demo

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  // gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(demo::gc_new_test);
  RUN_TEST(demo::gc_header_test);
  RUN_TEST(demo::endian_test);
  RUN_TEST(demo::dual_header_test);
  RUN_TEST(demo::union_test);

  // gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
