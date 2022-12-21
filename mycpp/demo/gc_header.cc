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
  unsigned is_header_ : 1;

  // - 0 is for user-defined classes
  // - 1 to 6 reserved for "tagless" value:
  // value_e.{Str,List,Dict,Bool,Int,Float}
  // - 7 to 127: ASDL union, so we have a maximuim of ~120 variants.
  unsigned type_tag_ : 7;

  #if MARK_SWEEP
  unsigned obj_id_ : 24;  // small index into mark bitmap, implies 16 Mi unique
                          // objects
  #else
  unsigned field_mask_ : 24;  // Cheney doesn't need obj_id, but needs
                              // field_mask AND obj_len
  #endif

#else
  // Possible 32-bit big endian version.  TODO: Put tests in
  // mycpp/portability_test.cc
  unsigned obj_id_ : 24;
  unsigned is_header_ : 1;
  unsigned type_tag_ : 7;
#endif

  // --- Second 32 bits ---

#if MARK_SWEEP
  // A fake "union", because unions and bitfields don't pack as you'd like
  unsigned heap_tag_ : 2;  // HeapTag::Opaque, HeapTag::Scanned, etc.
  unsigned u_mask_npointers_strlen_ : 30;
#else
  unsigned heap_tag_ : 3;  // also needs HeapTag::Forwarded
  unsigned obj_len_ : 29;
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
  #define FIELD_MASK(header) (header).u_mask_npointers_strlen_
  #define NUM_POINTERS(header) (header).u_mask_npointers_strlen_

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
  #define FIELD_MASK(header) (header).field_mask_

  // Derive num pointers from object length
  #define NUM_POINTERS(header) \
    (((header).obj_len_ - sizeof(ObjHeader)) / sizeof(void*))

#endif

TEST gc_header_test() {
  ObjHeader obj;
  // log("sizeof(Introspect) = %d", sizeof(Introspect));
  log("sizeof(ObjHeader) = %d", sizeof(ObjHeader));

  static_assert(sizeof(ObjHeader) == 8, "expected 8 byte header");

  obj.type_tag_ = 127;
  log("type tag %d", obj.type_tag_);

  obj.heap_tag_ = HeapTag::Scanned;
  log("heap tag %d", obj.heap_tag_);

  // obj.heap_tag = 4;  // Overflow
  // log("heap tag %d", obj.heap_tag_);

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

  static constexpr unsigned int field_mask() {
    return 0x30;
  }
};

class NoVirtual {
 public:
  NoVirtual() : GC_CLASS_FIXED(header_, field_mask(), sizeof(NoVirtual)) {
  }

  GC_OBJ(header_);
  int i;

  static constexpr unsigned int field_mask() {
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
  log("Derived is GC object? %d", header->type_tag_ & 0x1);

  NoVirtual n2;
  ObjHeader* header2 = reinterpret_cast<ObjHeader*>(&n2);
  log("NoVirtual is GC object? %d", header2->type_tag_ & 0x1);

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
  log("n->heap_tag %d", n->header_.heap_tag_);
  log("FIELD_MASK(n) %d", FIELD_MASK(n->header_));

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

class HeapStr {
 public:
  HeapStr() : GC_STR(header_) {
  }
  int Length() {
#ifdef MARK_SWEEP
    return header_.u_mask_npointers_strlen_;
#elif BUMP_LEAK
  #error "TODO: add field to HeapStr"
#else
    // derive string length from GC object length
    return header.obj_len_ - kStrHeaderSize - 1;
#endif
  }
  void SetLength(int len) {
    // Important invariant that makes str_equals() simpler: "abc" in a HeapStr
    // is INVALID.
    assert(len > kSmallStrThreshold);

#ifdef MARK_SWEEP
    header_.u_mask_npointers_strlen_ = len;
#elif BUMP_LEAK
  #error "TODO: add field to HeapStr"
#else
    // set object length, which can derive string length
    header.obj_len_ = kStrHeaderSize + len + 1;  // +1 for
#endif
  }
  ObjHeader header_;
  char data_[1];
};

constexpr int kStrHeaderSize = offsetof(HeapStr, data_);

// AllocHeapStr() is a helper that allocates a HeapStr but doesn't set its
// length.  It's NOT part of the public API; use NewStr() instead
static HeapStr* AllocHeapStr(int n) {
  void* place = malloc(kStrHeaderSize + n + 1);  // +1 for NUL terminator
  return new (place) HeapStr();
}

// Str is a value type that can be small or big!
union Str {
  // small_ is the whole 8 bytes
  Str(SmallStr small) : small_(small) {
  }
  // big_ may be 4 bytes, so we need raw_bytes_ first
  Str(HeapStr* big) : raw_bytes_(0) {
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

  // Mutate in place, like OverAllocatedStr then SetObjLenFromStrLen()
  // Assumes the caller already NUL-terminate the string to this length!
  // e.g. read(), snprintf
  void MaybeShrink(int new_len) {
    if (new_len <= kSmallStrThreshold) {
      if (small_.is_present_) {  // It's already small, just set length

        // Callers like strftime() should have NUL-terminated it!
        assert(small_.data_[new_len] == '\0');

        small_.length_ = new_len;

      } else {                        // Shrink from big to small
        HeapStr* copy_of_big = big_;  // Important!

        raw_bytes_ = 0;  // maintain invariants for fast str_equals()
        small_.is_present_ = 1;
        memcpy(small_.data_, copy_of_big->data_, new_len);
        small_.data_[new_len] = '\0';  // NUL terminate
      }
    } else {  // It's already bit, set length
      // OverAllocatedStr always starts with a big string
      assert(!small_.is_present_);

      // Callers like strftime() should have NUL-terminated it!
      assert(big_->data_[new_len] == '\0');

      big_->SetLength(new_len);
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

  uint64_t raw_bytes_;
  SmallStr small_;
  HeapStr* big_;
};

// Invariants affecting Str equality
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
// 2. OverAllocatedStr(), then MaybeShrink()
// 3. Str:: methods that use the above functions, or NewStr()

bool str_equals(Str a, Str b) {
  // Fast path takes care of two cases:  Identical small strings, or identical
  // pointers to big strings!
  if (a.raw_bytes_ == b.raw_bytes_) {
    return true;
  }

  bool a_small = a.IsSmall();
  bool b_small = b.IsSmall();

  // Str instances are normalized so a SmallStr can't equal a HeapStr*
  if (a_small != b_small) {
    return false;
  }

  // Both are small, and we already failed the fast path
  if (a_small) {
    return false;
  }

  // Both are big
  int a_len = a.big_->Length();
  int b_len = b.big_->Length();

  if (a_len != b_len) {
    return false;
  }

  return memcmp(a.big_->data_, b.big_->data_, a_len) == 0;
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

// NOTE: must call MaybeShrink(n) afterward to set length!  Should it NUL
// terminate?
Str OverAllocatedStr(int n) {
  // There's no point in overallocating small strings
  assert(n > kSmallStrThreshold);

  HeapStr* big = AllocHeapStr(n);
  // Not setting length!
  return Str(big);
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

  Str hostname = OverAllocatedStr(HOST_NAME_MAX);
  int status = ::gethostname(hostname.big_->data_, HOST_NAME_MAX);
  if (status != 0) {
    assert(0);
  }
  hostname.MaybeShrink(strlen(hostname.big_->data_));

  log("hostname = %s", hostname.c_str());

  time_t ts = 0;
  tm* loc_time = ::localtime(&ts);

  const int max_len = 1024;
  Str t1 = OverAllocatedStr(max_len);

  int n = strftime(t1.big_->data_, max_len, "%Y-%m-%d", loc_time);
  if (n == 0) {  // exceeds max length
    assert(0);
  }
  t1.MaybeShrink(n);

  log("t1 = %s", t1.c_str());

  Str t2 = OverAllocatedStr(max_len);
  n = strftime(t2.big_->data_, max_len, "%Y", loc_time);
  if (n == 0) {  // exceeds max length
    assert(0);
  }
  t2.MaybeShrink(n);

  log("t2 = %s", t2.c_str());

  // TODO:
  // BufWriter (rename StrWriter, and uses MutableHeapStr ?)
  //   writer.getvalue();  // may copy into data_

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

  RUN_TEST(demo::gc_header_test);
  RUN_TEST(demo::endian_test);
  RUN_TEST(demo::dual_header_test);
  RUN_TEST(demo::small_str_test);
  RUN_TEST(demo::union_test);

  // gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
