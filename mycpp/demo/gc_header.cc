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

  // Allocator is responsible for setting obj_id_
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

  unsigned obj_id_ : 24;  // implies 16 Mi unique objects
#else
  // Big endian version.  TODO: Put tests in mycpp/portability_test.

  unsigned obj_id_ : 24;

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
  #define FIELD_MASK(obj) (obj)->obj_id_

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

// SmallStr is used as a VALUE

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

// HeapStr is used as POINTER

class HeapStr : public Obj {
 public:
  // HeapStr() : Obj(Tag::Opaque, kZeroMask, kNoObjLen) {
  HeapStr() : Obj() {
  }
  int Length() {
    return STR_LEN(this);
  }
  void SetLength(int len) {
    // Important invariant that makes str_equals() simpler: "abc" in a HeapStr
    // is INVALID.
    assert(len > kSmallStrThreshold);

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

// Str is a value type that can be small or big!
union Str {
  Str(SmallStr small) : small_(small) {
    // small_ is the whole 8 bytes
  }
  Str(HeapStr* big) : raw_bytes_(0) {
    // big_ may be 4 bytes, so we need raw_bytes_ first
    big_ = big;
  }

  bool IsSmall() {
    return small_.is_present_;
  }

  // Returns a NUL-terminated C string, like std::string::c_str()
  char* c_str() {
    if (small_.is_present_) {
      return small_.data_;
    } else {
      return big_->data_;
    }
  }

  void CopyTo(char* dest) {
    char* src;
    int n;
    if (small_.is_present_) {
      src = small_.data_;
      n = small_.length_;
    } else {
      src = big_->data_;
      n = big_->Length();
    }
    memcpy(dest, src, n);
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
  uint64_t raw_bytes_;
  SmallStr small_;
  HeapStr* big_;
};

// Invariants affecting equality
//
// 1. The contents of Str are normalized
//  - SmallStr: the bytes past the NUL terminator are zero-initialized.
//  - HeapStr*: if sizeof(HeapStr*) == 4, then the rest of the bytes are
//    zero-initialized.
//
// 2.             If len(s) <= kSmallStrThreshold, then     s.IsSmall()
//    Conversely, If len(s) >  kSmallStrThreshold, then NOT s.IsSmall()
//
// This is enforced by the fact that all strings are created by:
//
// 1. StrFromC()
// 2. OverAllocatedStr(), then Shrink()
// 3. Str:: methods that use the above functions, or NewStr()

bool str_equals(Str a, Str b) {
  // Fast path takes care of two cases:  Identical small strings, or identical
  // pointers to big strings!
  if (a.raw_bytes_ == b.raw_bytes_) {
    return true;
  }

  // Str are normalized so a SmallStr can't equal a HeapStr*
  bool a_small = a.IsSmall();
  bool b_small = b.IsSmall();
  if (a_small != b_small) {
    return false;
  }

  if (a_small) {
    int a_len = a.small_.length_;
    int b_len = b.small_.length_;
    if (a_len != b_len) {
      return false;
    }
    return memcmp(a.small_.data_, b.small_.data_, a_len) == 0;
  } else {
    int a_len = a.big_->Length();
    int b_len = b.big_->Length();
    if (a_len != b_len) {
      return false;
    }
    return memcmp(a.big_->data_, b.big_->data_, a_len) == 0;
  }
}

#define G_SMALL_STR(name, s, small_len)          \
  GlobalSmallStr _##name = {1, 0, small_len, s}; \
  Str name = *(reinterpret_cast<Str*>(&_##name));

G_SMALL_STR(kEmptyString, "", 0);

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

Str str_concat(Str a, Str b) {
  int a_len = len(a);
  int b_len = len(b);
  int new_len = a_len + b_len;

  // Create both on the stack so we can share the logic
  HeapStr* big;
  SmallStr small(kSmallStrInvalidLength);

  char* dest;

  if (new_len <= kSmallStrThreshold) {
    dest = small.data_;
    small.length_ = new_len;
  } else {
    big = AllocHeapStr(new_len);

    dest = big->data_;
    big->SetLength(new_len);
  }

  a.CopyTo(dest);
  dest += a_len;

  b.CopyTo(dest);
  dest += b_len;

  *dest = '\0';

  if (new_len <= kSmallStrThreshold) {
    return Str(small);
  } else {
    return Str(big);
  }
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

  log("");
  log("---- str_concat() ---- ");
  log("");

  Str empty_empty = str_concat(kEmptyString, kEmptyString);
  ASSERT(empty_empty.IsSmall());
  log("empty_empty (%d) = %s", len(empty_empty), empty_empty.c_str());

  Str empty_small = str_concat(kEmptyString, StrFromC("b"));
  ASSERT(empty_small.IsSmall());
  log("empty_small (%d) = %s", len(empty_small), empty_small.c_str());

  Str small_small = str_concat(StrFromC("a"), StrFromC("b"));
  ASSERT(small_small.IsSmall());
  log("small_small (%d) %s", len(small_small), small_small.c_str());

  Str small_big = str_concat(StrFromC("small"), StrFromC("big string"));
  ASSERT(!small_big.IsSmall());
  log("small_big (%d) %s", len(small_big), small_big.c_str());

  Str big_small = str_concat(StrFromC("big string"), StrFromC("small"));
  ASSERT(!big_small.IsSmall());
  log("big_small (%d) %s", len(big_small), big_small.c_str());

  Str big_big = str_concat(StrFromC("abcdefghij"), StrFromC("0123456789"));
  ASSERT(!big_big.IsSmall());
  log("big_big (%d) = %s ", len(big_big), big_big.c_str());

  log("");
  log("---- str_equals() ---- ");
  log("");

  ASSERT(str_equals(kEmptyString, StrFromC("")));
  ASSERT(str_equals(kEmptyString, NewStr(0)));

  // small vs. small
  ASSERT(!str_equals(kEmptyString, StrFromC("a")));

  ASSERT(str_equals(StrFromC("a"), StrFromC("a")));
  ASSERT(!str_equals(StrFromC("a"), StrFromC("b")));    // same length
  ASSERT(!str_equals(StrFromC("a"), StrFromC("two")));  // different length

  // small vs. big
  ASSERT(!str_equals(StrFromC("small"), StrFromC("big string")));
  ASSERT(!str_equals(StrFromC("big string"), StrFromC("small")));

  // big vs. big
  ASSERT(str_equals(StrFromC("big string"), StrFromC("big string")));
  ASSERT(!str_equals(StrFromC("big string"), StrFromC("big strinZ")));
  ASSERT(!str_equals(StrFromC("big string"), StrFromC("longer string")));

  // TODO:
  log("");
  log("---- OverAllocatedStr() ---- ");
  log("");

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
  //   short HeapStr? But as long as they use NewStr() and OverAllocatedStr()
  //   APIs correctly, they will never get a HeapStr?
  //
  //   Invariant: it's IMPOSSIBLE to create a HeapStr directly?  Yes I think so

  PASS();
}

//
// Union test
//

//
// header_.not_vtable  // 1 bit
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

union ObjHeader {
  // doesn't work: initializations for multiple members?
  // ObjHeader() : raw_bytes(0), is_header(1) {

  // also doesn't work
  // ObjHeader() : is_header(1), type_tag(1) {

  ObjHeader() : raw_bytes(0) {
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
    this->heap_tag.val = Tag::FixedSize;
    this->field_mask.val = field_mask;
  }

  // - Slab<List*>, Slab<Str> (might be HeapStr*)
  // - Generated classes without inheritance
  // - all ASDL types
  void InitScanned(int num_pointers) {
    this->is_header.val = 1;
    this->heap_tag.val = Tag::Scanned;
    this->num_pointers.val = num_pointers;
  }

  void InitStr(int str_len) {
    this->is_header.val = 1;
    this->heap_tag.val = Tag::Opaque;
    this->str_len.val = str_len;
  }

  void InitAsdlVariant(int type_tag, int num_pointers) {
    this->is_header.val = 1;

    this->type_tag.val = type_tag;

    this->heap_tag.val = Tag::Scanned;
    this->num_pointers.val = num_pointers;
  }

  // Other:
  // - Tag::Global is for GlobalBigStr*, GLOBAL_LIST, ...
  //
  // All the variants of value_e get their own type tag?
  // - Boxed value.{Bool,Int,Float}
  // - And "boxless" / "tagless" Str, List, Dict

};

class Token {
 public:
  Token() : header_() {
  }

  ObjHeader header_;
};

TEST union_test() {
  Token t;

  t.header_.is_header.val = 1;

  t.header_.type_tag.val = 127;
  t.header_.obj_id.val = 12345678;  // max 16 Mi

  t.header_.heap_tag.val = Tag::Scanned;
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
  ObjHeader* obj = reinterpret_cast<ObjHeader*>(&t);

  // Then check for vtable - it might not be a pointer to an ObjHeader
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
  RUN_TEST(demo::dual_header_test);
  RUN_TEST(demo::small_str_test);
  RUN_TEST(demo::union_test);

  // gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
