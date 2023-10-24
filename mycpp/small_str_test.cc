// small_str_test.cc - Demo for new BigStr implementation

#include <inttypes.h>
#include <limits.h>  // HOST_NAME_MAX
#include <unistd.h>  // gethostname()

#include <new>  // placement new

// #include "mycpp/runtime.h"
#include "mycpp/common.h"
#include "mycpp/gc_obj.h"  // ObjHeader
#include "vendor/greatest.h"

namespace small_str_test {

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
  HeapStr() {
  }
  int Length() {
#ifdef MARK_SWEEP
    return header_.u_mask_npointers;
#elif BUMP_LEAK
  #error "TODO: add field to HeapStr"
#else
    // derive string length from GC object length
    return header.obj_len - kStrHeaderSize - 1;
#endif
  }
  void SetLength(int len) {
    // Important invariant that makes str_equals() simpler: "abc" in a HeapStr
    // is INVALID.
    assert(len > kSmallStrThreshold);

#ifdef MARK_SWEEP
    header_.u_mask_npointers = len;
#elif BUMP_LEAK
  #error "TODO: add field to HeapStr"
#else
    // set object length, which can derive string length
    header.obj_len = kStrHeaderSize + len + 1;  // +1 for
#endif
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::BigStr();
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

// BigStr is a value type that can be small or big!
union BigStr {
  // small_ is the whole 8 bytes
  BigStr(SmallStr small) : small_(small) {
  }
  // big_ may be 4 bytes, so we need raw_bytes_ first
  BigStr(HeapStr* big) : raw_bytes_(0) {
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

  BigStr upper() {
    if (small_.is_present_) {
      // Mutate
      for (int i = 0; i < small_.length_; ++i) {
        small_.data_[i] = toupper(small_.data_[i]);
      }
      return BigStr(small_);  // return a copy BY VALUE
    } else {
      int n = big_->Length();
      HeapStr* result = AllocHeapStr(n);

      for (int i = 0; i < n; ++i) {
        result->data_[i] = toupper(big_->data_[i]);
      }
      result->data_[n] = '\0';
      result->SetLength(n);

      return BigStr(result);
    }
  }

  uint64_t raw_bytes_;
  SmallStr small_;
  HeapStr* big_;
};

// Invariants affecting BigStr equality
//
// 1. The contents of BigStr are normalized
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
// 3. BigStr:: methods that use the above functions, or NewStr()

bool str_equals(BigStr a, BigStr b) {
  // Fast path takes care of two cases:  Identical small strings, or identical
  // pointers to big strings!
  if (a.raw_bytes_ == b.raw_bytes_) {
    return true;
  }

  bool a_small = a.IsSmall();
  bool b_small = b.IsSmall();

  // BigStr instances are normalized so a SmallStr can't equal a HeapStr*
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
  BigStr name = *(reinterpret_cast<BigStr*>(&_##name));

G_SMALL_STR(kEmptyString, "", 0);

G_SMALL_STR(gSmall, "global", 6);

BigStr NewStr(int n) {
  if (n <= kSmallStrThreshold) {
    SmallStr small(n);
    return BigStr(small);
  } else {
    HeapStr* big = AllocHeapStr(n);
    big->SetLength(n);
    return BigStr(big);
  }
}

// NOTE: must call MaybeShrink(n) afterward to set length!  Should it NUL
// terminate?
BigStr OverAllocatedStr(int n) {
  // There's no point in overallocating small strings
  assert(n > kSmallStrThreshold);

  HeapStr* big = AllocHeapStr(n);
  // Not setting length!
  return BigStr(big);
}

BigStr StrFromC(const char* s, int n) {
  if (n <= kSmallStrThreshold) {
    SmallStr small(n);
    memcpy(small.data_, s, n + 1);  // copy NUL terminator too
    return BigStr(small);
  } else {
    HeapStr* big = AllocHeapStr(n);
    memcpy(big->data_, s, n + 1);  // copy NUL terminator too
    big->SetLength(n);
    return BigStr(big);
  }
}

BigStr StrFromC(const char* s) {
  return StrFromC(s, strlen(s));
}

int len(BigStr s) {
  if (s.small_.is_present_) {
    return s.small_.length_;
  } else {
    return s.big_->Length();
  }
}

BigStr str_concat(BigStr a, BigStr b) {
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
    return BigStr(small);
  } else {
    return BigStr(big);
  }
}

static_assert(sizeof(SmallStr) == 8, "SmallStr should be 8 bytes");
static_assert(sizeof(BigStr) == 8, "BigStr should be 8 bytes");

TEST small_str_test() {
  log("sizeof(BigStr) = %d", sizeof(BigStr));
  log("sizeof(SmallStr) = %d", sizeof(SmallStr));
  log("sizeof(HeapStr*) = %d", sizeof(HeapStr*));

  log("");
  log("---- SmallStrFromC() / StrFromC() / global G_SMALL_STR() ---- ");
  log("");

  log("gSmall = %s", gSmall.small_.data_);

  // BigStr s { 1, 0, 3, "foo" };
  SmallStr local_small(0);
  ASSERT(local_small.is_present_);

  // It just has 1 bit set
  log("local_small as integer %d", local_small);
  log("local_small = %s", local_small.data_);

  BigStr local_s = StrFromC("little");
  ASSERT(local_s.IsSmall());
  log("local_s = %s", local_s.small_.data_);

  BigStr local_big = StrFromC("big long string");
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

  BigStr u1 = local_s.upper();
  ASSERT(u1.IsSmall());

  BigStr u2 = gSmall.upper();
  ASSERT(u2.IsSmall());

  BigStr u3 = local_big.upper();
  ASSERT(!u3.IsSmall());

  log("local_small = %s %d", u1.c_str(), len(u1));
  log("gSmall = %s %d", u2.c_str(), len(u2));
  log("local_big = %s %d", u3.c_str(), len(u3));

  log("");
  log("---- NewStr() ---- ");
  log("");

  BigStr small_empty = NewStr(6);
  ASSERT(small_empty.IsSmall());
  ASSERT_EQ(6, len(small_empty));

  BigStr big_empty = NewStr(7);
  ASSERT(!big_empty.IsSmall());
  ASSERT_EQ_FMT(7, len(big_empty), "%d");

  log("");
  log("---- str_concat() ---- ");
  log("");

  BigStr empty_empty = str_concat(kEmptyString, kEmptyString);
  ASSERT(empty_empty.IsSmall());
  log("empty_empty (%d) = %s", len(empty_empty), empty_empty.c_str());

  BigStr empty_small = str_concat(kEmptyString, StrFromC("b"));
  ASSERT(empty_small.IsSmall());
  log("empty_small (%d) = %s", len(empty_small), empty_small.c_str());

  BigStr small_small = str_concat(StrFromC("a"), StrFromC("b"));
  ASSERT(small_small.IsSmall());
  log("small_small (%d) %s", len(small_small), small_small.c_str());

  BigStr small_big = str_concat(StrFromC("small"), StrFromC("big string"));
  ASSERT(!small_big.IsSmall());
  log("small_big (%d) %s", len(small_big), small_big.c_str());

  BigStr big_small = str_concat(StrFromC("big string"), StrFromC("small"));
  ASSERT(!big_small.IsSmall());
  log("big_small (%d) %s", len(big_small), big_small.c_str());

  BigStr big_big = str_concat(StrFromC("abcdefghij"), StrFromC("0123456789"));
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

  BigStr hostname = OverAllocatedStr(HOST_NAME_MAX);
  int status = ::gethostname(hostname.big_->data_, HOST_NAME_MAX);
  if (status != 0) {
    assert(0);
  }
  hostname.MaybeShrink(strlen(hostname.big_->data_));

  log("hostname = %s", hostname.c_str());

  time_t ts = 0;
  tm* loc_time = ::localtime(&ts);

  const int max_len = 1024;
  BigStr t1 = OverAllocatedStr(max_len);

  int n = strftime(t1.big_->data_, max_len, "%Y-%m-%d", loc_time);
  if (n == 0) {  // exceeds max length
    assert(0);
  }
  t1.MaybeShrink(n);

  log("t1 = %s", t1.c_str());

  BigStr t2 = OverAllocatedStr(max_len);
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

}  // namespace small_str_test

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  // gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(small_str_test::small_str_test);

  // gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
