#include <new>  // placement new

#include "mycpp/common.h"  // for log()
#include "vendor/greatest.h"

namespace demo {

// This is 8 bytes!  Unions and bitfields don't work together?
struct UnionBitfield {
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

// Could put this in ./configure, although glibc seems to have it
bool IsLittleEndian() {
  int i = 42;
  int* pointer_i = &i;
  char c = *(reinterpret_cast<char*>(pointer_i));

  // Should be 42 on little endian, 0 on big endian
  return c == 42;
}

//
// NEW OBJECT HEADER
//

class Obj {
 public:
  Obj() {
  }

  // Allocator is responsible for setting obj_id
  Obj(int heap_tag, int u_mask_npointers_strlen)
      : type_tag_(1),  // must be odd
        heap_tag_(heap_tag),
        u_mask_npointers_strlen_(u_mask_npointers_strlen) {
  }

#if LITTLE_ENDIAN

  // First 32 bits
  unsigned type_tag_ : 8;  // for ASDL: max of 128 variants in a sum type
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

  // type_tag must be odd
  //
  // - 1 for user-defined class
  //
  // reserved for "tagless" value_e ?
  // - 3 value_e.Str is Str
  // - 5 value_e.List
  // - 7 value_e.Dict
  // - 9 value_e.Bool
  // - 11 value_e.Int
  // - 13 value_e.Float
  //
  // - 15 to 255: ASDL union.  So that's about 115 variants allowed.

  unsigned type_tag_ : 8;
#endif

  // Second 32 bits
  unsigned heap_tag_ : 2;

  // a "union", because struct bitfields and union bitfield don't pack well
  // For Cheney, this is OBJECT length
  unsigned u_mask_npointers_strlen_ : 30;
};

#define FIELD_MASK(obj) (obj)->u_mask_npointers_strlen_
#define NUM_POINTERS(obj) (obj)->u_mask_npointers_strlen_
#define STR_LEN(obj) (obj)->u_mask_npointers_strlen_

#ifdef MARK_SWEEP
  // mark-sweep throws away obj_len
  #define WITH_HEADER(tag, field_mask, obj_len) Obj(tag, field_mask)

// Str header: STRLEN in u_mask_npointers_strlen_
// Slab header: NPOINTERS in u_mask_npointers_strlen_

#else
  // Cheney uses obj_len
  #define WITH_HEADER(tag, field_mask, obj_len) Obj(tag, field_mask, obj_len)

  // Store obj_len in 30-bit field (1 Gi strings)
  #define OBJ_LEN(obj) (obj)->u_mask_npointers_strlen_
  // Store field_mask in 24-bit field (~24 fields with inheritance)
  #define FIELD_MASK(obj) (obj)->obj_id

// Str header: OBJLEN u_mask_npointers_strlen_, deriving STRLEN
// Slab header: OBJLEN length in u_mask_npointers_strlen_, deriving NPOINTERS
#endif

TEST gc_header_test() {
  Obj obj;
  // log("sizeof(Introspect) = %d", sizeof(Introspect));
  log("sizeof(Obj) = %d", sizeof(Obj));
  log("sizeof(UnionBitfield) = %d", sizeof(UnionBitfield));

  static_assert(sizeof(Obj) == 8);

  obj.type_tag_ = 255;
  log("type tag %d", obj.type_tag_);

  obj.heap_tag_ = Tag::Scanned;
  log("heap tag %d", obj.heap_tag_);

  // obj.heap_tag = 4;  // Overflow
  // log("heap tag %d", obj.heap_tag_);

  FIELD_MASK(&obj) = 0b11;
  log("field mask %d", FIELD_MASK(&obj));
  log("num pointers %d", NUM_POINTERS(&obj));
  log("str len %d", STR_LEN(&obj));

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
  log("Derived is GC object? %d", obj->type_tag_ & 0x1);

  NoVirtual n2;
  Obj* obj2 = reinterpret_cast<Obj*>(&n2);
  log("NoVirtual is GC object? %d", obj2->type_tag_ & 0x1);

  PASS();
}

// #if MARK_SWEEP -> change to #if CHENEY_SEMI
// #if BUMP_LEAK

TEST dual_header_test() {
  auto* n = new Node();
  log("n = %p", n);
  log("n->heap_tag %d", n->heap_tag_);
  log("FIELD_MASK(*n) %d", FIELD_MASK(n));

  PASS();
}

//
// STRING IMPLEMENTATION
//

class HeapStr : public Obj {
 public:
  // HeapStr() : Obj(Tag::Opaque, kZeroMask, kNoObjLen) {
  HeapStr() : Obj() {
  }
  int Length() {
    return STR_LEN(this);
  }
  void SetLength(int len) {
    STR_LEN(this) = len;
  }
  char data_[1];
};

// AllocHeapStr() is a helper that allocates a HeapStr but doesn't set its
// length.  It's NOT part of the public API; use NewStr() instead
static HeapStr* AllocHeapStr(int n) {
  void* place = malloc(sizeof(Obj) + n + 1);  // +1 for NUL terminator
  return new (place) HeapStr();
}

const int kSmallStrThreshold = 6;
const int kSmallStrInvalidLength = 0b1111;

// Layout compatible with SmallStr, and globally initialized
struct GlobalSmallStr {
  unsigned is_present_ : 1;  // reserved
  unsigned pad_ : 3;
  unsigned length_ : 4;  // max string length is 6

  char data_[7];  // NUL-terminated C string
};

// SmallStr is an 8-byte value type (even on 32-bit machines)
class SmallStr {
 public:
  SmallStr(int n) : is_present_(1), pad_(0), length_(n), data_{0} {
  }

  unsigned is_present_ : 1;  // reserved
  unsigned pad_ : 3;
  unsigned length_ : 4;  // 0 to 6 bytes of data payload

  char data_[7];
};

// Str is a value type that can be small or big!
union Str {
  Str(SmallStr small) : small_(small) {
    // small_ is the whole 8 bytes
  }
  Str(HeapStr* big) : zero_init(0) {
    // big_ may be 4 bytes, so we need zero_init first
    big_ = big;
  }

  bool IsSmall() {
    return small_.is_present_;
  }

  char* c_str() {
    if (small_.is_present_) {
      return small_.data_;  // NUL terminated
    } else {
      return big_->data_;
    }
  }

  Str upper() {
    if (small_.is_present_) {
      // Mutate
      for (int i = 0; i < small_.length_; ++i) {
        small_.data_[i] = toupper(small_.data_[i]);
      }
      return Str(small_);  // return a copy BY VALUE
    } else {
      int n = big_->Length();
      HeapStr* result = AllocHeapStr(n);

      for (int i = 0; i < n; ++i) {
        result->data_[i] = toupper(big_->data_[i]);
      }
      result->data_[n] = '\0';
      result->SetLength(n);

      return Str(result);
    }
  }

  // private:
  uint64_t zero_init;
  SmallStr small_;
  HeapStr* big_;
};

#define G_SMALL_STR(name, s, small_len)          \
  GlobalSmallStr _##name = {1, 0, small_len, s}; \
  Str name = *(reinterpret_cast<Str*>(&_##name));

G_SMALL_STR(gSmall, "global", 6);

Str NewStr(int n) {
  if (n <= kSmallStrThreshold) {
    SmallStr small(n);
    return Str(small);
  } else {
    HeapStr* big = AllocHeapStr(n);
    big->SetLength(n);
    return Str(big);
  }
}

// NOTE: must call Shrink(n) afterward to set length!  Should it NUL terminate?
Str OverAllocatedStr(int n) {
  if (n <= kSmallStrThreshold) {
    SmallStr small(kSmallStrInvalidLength);
    return Str(small);
  } else {
    HeapStr* big = AllocHeapStr(n);
    // Not setting length!
    return Str(big);
  }
}

Str StrFromC(const char* s, int n) {
  if (n <= kSmallStrThreshold) {
    SmallStr small(n);
    memcpy(small.data_, s, n + 1);  // copy NUL terminator too
    return Str(small);
  } else {
    HeapStr* big = AllocHeapStr(n);
    memcpy(big->data_, s, n + 1);  // copy NUL terminator too
    big->SetLength(n);
    return Str(big);
  }
}

Str StrFromC(const char* s) {
  return StrFromC(s, strlen(s));
}

int len(Str s) {
  if (s.small_.is_present_) {
    return s.small_.length_;
  } else {
    return s.big_->Length();
  }
}

static_assert(sizeof(Str) == 8);

bool str_equals(Str a, Str b) {
  assert(0);
  // return true;
}

Str str_concat(Str a, Str b) {
  // TODO: implement this
  //
  // Probably with Str::CopyTo(char* dest)
  assert(0);
}

static_assert(sizeof(SmallStr) == 8);
static_assert(sizeof(Str) == 8);

TEST small_str_test() {
  log("sizeof(Str) = %d", sizeof(Str));
  log("sizeof(SmallStr) = %d", sizeof(SmallStr));
  log("sizeof(HeapStr*) = %d", sizeof(HeapStr*));

  log("");
  log("---- SmallStrFromC() / StrFromC() / global G_SMALL_STR() ---- ");
  log("");

  log("gSmall = %s", gSmall.small_.data_);

  // Str s { 1, 0, 3, "foo" };
  SmallStr local_small(0);
  ASSERT(local_small.is_present_);

  // It just has 1 bit set
  log("local_small as integer %d", local_small);
  log("local_small = %s", local_small.data_);

  Str local_s = StrFromC("little");
  ASSERT(local_s.IsSmall());
  log("local_s = %s", local_s.small_.data_);

  Str local_big = StrFromC("big long string");
  ASSERT(!local_big.IsSmall());

  log("");
  log("---- c_str() ---- ");
  log("");

  log("gSmall = %s %d", gSmall.c_str(), len(gSmall));
  log("local_small = %s %d", local_s.c_str(), len(local_s));
  log("local_big = %s %d", local_big.c_str(), len(local_big));

  log("");
  log("---- Str_upper() ---- ");
  log("");

  Str u1 = local_s.upper();
  ASSERT(u1.IsSmall());

  Str u2 = gSmall.upper();
  ASSERT(u2.IsSmall());

  Str u3 = local_big.upper();
  ASSERT(!u3.IsSmall());

  log("local_small = %s %d", u1.c_str(), len(u1));
  log("gSmall = %s %d", u2.c_str(), len(u2));
  log("local_big = %s %d", u3.c_str(), len(u3));

  log("");
  log("---- NewStr() ---- ");
  log("");

  Str small_empty = NewStr(6);
  ASSERT(small_empty.IsSmall());
  ASSERT_EQ(6, len(small_empty));

  Str big_empty = NewStr(7);
  ASSERT(!big_empty.IsSmall());
  ASSERT_EQ_FMT(7, len(big_empty), "%d");

  // TODO:
  //
  log("");
  log("---- OverAllocatedStr() ---- ");
  log("");

  log("");
  log("---- str_equals() ---- ");
  log("");

  log("");
  log("---- str_concat() ---- ");
  log("");

#if 0
  // I don't want typedef uint64_t Str because I want more type safety than
  // this !!!
  log("len(42) = %d", len(42));
#endif

  PASS();
}

// TODO:
//
// OverAllocatedStr()
//   mystr.Shrink(3);  // may copy into data_
//
// BufWriter (rename StrWriter, and uses MutableHeapStr ?)
//   writer.getvalue();  // may copy into data_
//
// str_equals() -- also used for hashing
//   not clear: should we take care of the case where an OS binding creates a
//   short HeapStr? But as long as they use NewStr() and OverAllocatedStr() APIs
//   correctly, they will never get a HeapStr?
//
//   Invariant: it's IMPOSSIBLE to create a HeapStr directly?  Yes I think so

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
