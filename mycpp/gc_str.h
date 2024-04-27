#ifndef MYCPP_GC_STR_H
#define MYCPP_GC_STR_H

#include "mycpp/common.h"  // DISALLOW_COPY_AND_ASSIGN
#include "mycpp/gc_obj.h"  // GC_OBJ
#include "mycpp/hash.h"    // HashFunc

template <typename T>
class List;

class BigStr {
 public:
  // Don't call this directly.  Call NewStr() instead, which calls this.
  BigStr() {
  }

  char* data() {
    return data_;
  }

  // Call this after writing into buffer created by OverAllocatedStr()
  void MaybeShrink(int str_len);

  BigStr* at(int i);

  int find(BigStr* needle, int start = 0, int end = -1);
  int rfind(BigStr* needle);

  BigStr* slice(int begin);
  BigStr* slice(int begin, int end);

  BigStr* strip();
  // Used for CommandSub in osh/cmd_exec.py
  BigStr* rstrip(BigStr* chars);
  BigStr* rstrip();

  BigStr* lstrip(BigStr* chars);
  BigStr* lstrip();

  BigStr* ljust(int width, BigStr* fillchar);
  BigStr* rjust(int width, BigStr* fillchar);

  // Can take (start, end) so Tokens can be compared without allocation
  bool startswith(BigStr* s);
  bool endswith(BigStr* s);

  BigStr* replace(BigStr* old, BigStr* new_str);
  BigStr* replace(BigStr* old, BigStr* new_str, int count);
  BigStr* join(List<BigStr*>* items);

  List<BigStr*>* split(BigStr* sep);
  List<BigStr*>* split(BigStr* sep, int max_split);
  List<BigStr*>* splitlines(bool keep);

  // TODO: Move unicode functions out of mycpp runtime?  Because we won't match
  // Python exactly
  bool isdigit();
  bool isalpha();
  bool isupper();

  BigStr* upper();
  BigStr* lower();

  // Other options for fast comparison / hashing / string interning:
  // - unique_id_: an index into intern table.  I don't think this works unless
  //   you want to deal with rehashing all strings when the set grows.
  //   - although note that the JVM has -XX:StringTableSize=FIXED, which means
  //   - it can degrade into linked list performance
  // - Hashed strings become GLOBAL_STR().  Never deallocated.
  // - Hashed strings become part of the "large object space", which might be
  //   managed by mark and sweep.  This requires linked list overhead.
  //   (doubly-linked?)
  // - Intern strings at GARBAGE COLLECTION TIME, with
  //   LayoutForwarded::new_location_?  Is this possible?  Does it introduce
  //   too much coupling between strings, hash tables, and GC?

  static constexpr ObjHeader obj_header() {
    return ObjHeader::BigStr();
  }

  unsigned hash(HashFunc h);

  int len_;
  unsigned hash_ : 31;
  unsigned is_hashed_ : 1;
  char data_[1];  // flexible array

 private:
  int _strip_left_pos();
  int _strip_right_pos();

  DISALLOW_COPY_AND_ASSIGN(BigStr)
};

constexpr int kStrHeaderSize = offsetof(BigStr, data_);

// Note: for SmallStr, we might copy into the VALUE
inline void BigStr::MaybeShrink(int str_len) {
  len_ = str_len;
  data_[len_] = '\0';  // NUL terminate
}

inline int len(const BigStr* s) {
  return s->len_;
}

BigStr* StrFormat(const char* fmt, ...);
BigStr* StrFormat(BigStr* fmt, ...);

// NOTE: This iterates over bytes.
class StrIter {
 public:
  explicit StrIter(BigStr* s) : s_(s), i_(0), len_(len(s)) {
    // Cheney only: s_ could be moved during iteration.
    // gHeap.PushRoot(reinterpret_cast<RawObject**>(&s_));
  }
  ~StrIter() {
    // gHeap.PopRoot();
  }
  void Next() {
    i_++;
  }
  bool Done() {
    return i_ >= len_;
  }
  BigStr* Value();  // similar to at()

 private:
  BigStr* s_;
  int i_;
  int len_;

  DISALLOW_COPY_AND_ASSIGN(StrIter)
};

extern BigStr* kEmptyString;

// GlobalStr notes:
// - sizeof("foo") == 4, for the NUL terminator.
// - gc_heap_test.cc has a static_assert that GlobalStr matches BigStr.  We
// don't put it here because it triggers -Winvalid-offsetof

template <int N>
class GlobalStr {
  // A template type with the same layout as BigStr with length N-1 (which needs
  // a buffer of size N).  For initializing global constant instances.
 public:
  int len_;
  unsigned hash_ : 31;
  unsigned is_hashed_ : 1;
  const char data_[N];

  DISALLOW_COPY_AND_ASSIGN(GlobalStr)
};

union Str {
 public:
  // Instead of this at the start of every function:
  //   Str* s = nullptr;
  // It will now be:
  //   Str s(nullptr);
  //
  //   StackRoot _root(&s);
  explicit Str(BigStr* big) : big_(big) {
  }

  char* data() {
    return big_->data();
  }

  Str at(int i) {
    return Str(big_->at(i));
  }

  Str upper() {
    return Str(big_->upper());
  }

  uint64_t raw_bytes_;
  BigStr* big_;
  // TODO: add SmallStr, see mycpp/small_str_test.cc
};

inline int len(const Str s) {
  return len(s.big_);
}

// This macro is a workaround for the fact that it's impossible to have a
// a constexpr initializer for char[N].  The "String Literals as Non-Type
// Template Parameters" feature of C++ 20 would have done it, but it's not
// there.
//
// https://old.reddit.com/r/cpp_questions/comments/j0khh6/how_to_constexpr_initialize_class_member_thats/
// https://stackoverflow.com/questions/10422487/how-can-i-initialize-char-arrays-in-a-constructor
//
// TODO: Can we hash values at compile time so they can be in the intern table?

#define GLOBAL_STR(name, val)                                                \
  GcGlobal<GlobalStr<sizeof(val)>> _##name = {                               \
      ObjHeader::Global(TypeTag::BigStr),                                    \
      {.len_ = sizeof(val) - 1, .hash_ = 0, .is_hashed_ = 0, .data_ = val}}; \
  BigStr* name = reinterpret_cast<BigStr*>(&_##name.obj);

// New style for SmallStr compatibility
#define GLOBAL_STR2(name, val)                                               \
  GcGlobal<GlobalStr<sizeof(val)>> _##name = {                               \
      ObjHeader::Global(TypeTag::BigStr),                                    \
      {.len_ = sizeof(val) - 1, .hash_ = 0, .is_hashed_ = 0, .data_ = val}}; \
  Str name(reinterpret_cast<BigStr*>(&_##name.obj));

// Helper function that's consistent with JSON definition of ASCII whitespace,
// e.g.
// {"age": \t 42} is OK
// {"age": \v 42} is NOT OK
inline bool IsAsciiWhitespace(int ch) {
  return ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n';
}

#endif  // MYCPP_GC_STR_H
