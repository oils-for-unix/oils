#include <inttypes.h>
#include <limits.h>  // HOST_NAME_MAX
#include <string.h>  // memcpy()
#include <time.h>    // strftime()
#include <unistd.h>  // gethostname()

#include <new>  // placement new

#include "mycpp/common.h"  // log()
#include "mycpp/gc_obj.h"  // ObjHeader
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

#define GC_NEW(T, ...)                                                \
  LayoutGc* untyped = gHeap.Allocate();                               \
  T* obj = new (untyped.place)(...) untyped.header = T::obj_header(); \
  untyped.header.obj_id = gHeap.mark_set_.NextObjectId() return obj

class Point {
 public:
  int x;
  int y;

  int vtag() {
    char* p = reinterpret_cast<char*>(this);
    ObjHeader* header = reinterpret_cast<ObjHeader*>(p - sizeof(ObjHeader));
    return header->type_tag;
  }

  static constexpr ObjHeader obj_header() {
    // type_tag is 42
    return ObjHeader::Global(42);
  }
};

// Alloc<T> allocates an instance of T and fills in the GC header BEFORE the
// object, and BEFORE any vtable (for classes with virtual functions).
//
// Alloc<T> is nicer for static dispatch; GC_NEW(T, ...) would be awkward.

// Steps to initialize a GC object:
//
// 1. Allocate untyped data
// 2. Fill in constexpr header data
// 3. Fill in DYNAMIC header data, like object ID
// 4. Invoke constructor with placement new

struct LayoutGc {
  ObjHeader header;
  uint8_t place[1];  // flexible array, for placement new
};

template <typename T>
T* Alloc() {
  // TODO: use gHeap.Allocate()

  LayoutGc* untyped =
      static_cast<LayoutGc*>(malloc(sizeof(ObjHeader) + sizeof(T)));
  untyped->header = T::obj_header();

  // TODO: assign proper object ID from MarkSweepHeap
  untyped->header.obj_id = 124;  // dynamic, but can be done by allocator
  return new (untyped->place) T();
}

TEST gc_header_test() {
  Point* p = Alloc<Point>();
  log("p = %p", p);

  log("p->vtag() = %d", p->vtag());
  ASSERT_EQ_FMT(42, p->vtag(), "%d");

  PASS();
}

class Node {
 public:
  Node() {
  }

  virtual int Method() {
    return 42;
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(Node));
  }

  int x;
  // max is either 24 or 30 bits, so use unsigned int
  static constexpr unsigned int field_mask() {
    return 0x0f;
  }
};

class Derived : public Node {
 public:
  Derived() : Node() {
  }

  virtual int Method() {
    return 43;
  }

  int x;

  static constexpr unsigned field_mask() {
    return Node::field_mask() | 0x30;
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(Derived));
  }
};

class NoVirtual {
 public:
  NoVirtual() {
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(NoVirtual));
  }

  int i;

  static constexpr unsigned field_mask() {
    return 0xf0;
  }
};

// TODO: Put this in mycpp/portability_test.cc and distribute to users

TEST endian_test() {
  log("little endian? %d", IsLittleEndian());

  Derived* derived = Alloc<Derived>();
  log("sizeof(Node) = %d", sizeof(Node));
  log("sizeof(Derived) = %d", sizeof(Derived));

  ObjHeader* header = ObjHeader::FromObject(derived);
  log("Derived is GC object? %d", header->type_tag & 0x1);

  NoVirtual* n2 = Alloc<NoVirtual>();
  ObjHeader* header2 = ObjHeader::FromObject(n2);
  log("NoVirtual is GC object? %d", header2->type_tag & 0x1);

  Node* n = Alloc<Node>();
  ObjHeader* h = ObjHeader::FromObject(n);
  FIELD_MASK(*h) = 0b11;
  log("field mask %d", FIELD_MASK(*h));
  log("num pointers %d", NUM_POINTERS(*h));

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
  Token() {
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

  RUN_TEST(demo::gc_header_test);
  RUN_TEST(demo::endian_test);
  RUN_TEST(demo::union_test);

  // gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
