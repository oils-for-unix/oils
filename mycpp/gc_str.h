#ifndef MYCPP_GC_STR_H
#define MYCPP_GC_STR_H

#include "mycpp/common.h"  // DISALLOW_COPY_AND_ASSIGN
#include "mycpp/gc_obj.h"  // GC_OBJ

template <typename T>
class List;

class Str {
 public:
  // Don't call this directly.  Call NewStr() instead, which calls this.
  Str() {
  }

  char* data() {
    return data_;
  }

  // Call this after writing into buffer created by OverAllocatedStr()
  void MaybeShrink(int str_len);

  Str* index_(int i);

  int find(Str* needle, int pos = 0);
  int rfind(Str* needle);

  Str* slice(int begin);
  Str* slice(int begin, int end);
  Str* slice(int begin, int end, int step);

  Str* strip();
  // Used for CommandSub in osh/cmd_exec.py
  Str* rstrip(Str* chars);
  Str* rstrip();

  Str* lstrip(Str* chars);
  Str* lstrip();

  Str* ljust(int width, Str* fillchar);
  Str* rjust(int width, Str* fillchar);

  bool startswith(Str* s);
  bool endswith(Str* s);

  Str* replace(Str* old, Str* new_str);
  Str* join(List<Str*>* items);

  List<Str*>* split(Str* sep);
  List<Str*>* split(Str* sep, int max_split);
  List<Str*>* splitlines(bool keep);

  bool isdigit();
  bool isalpha();
  bool isupper();

  Str* upper();
  Str* lower();

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
    return ObjHeader::Str();
  }

  int len_;
  int hash_value_;
  char data_[1];  // flexible array

 private:
  int _strip_left_pos();
  int _strip_right_pos();

  DISALLOW_COPY_AND_ASSIGN(Str)
};

constexpr int kStrHeaderSize = offsetof(Str, data_);

// Note: for SmallStr, we might copy into the VALUE
inline void Str::MaybeShrink(int str_len) {
  len_ = str_len;
  data_[len_] = '\0';  // NUL terminate
}

inline int len(const Str* s) {
  return s->len_;
}

Str* StrFormat(const char* fmt, ...);
Str* StrFormat(Str* fmt, ...);

// NOTE: This iterates over bytes.
class StrIter {
 public:
  explicit StrIter(Str* s) : s_(s), i_(0), len_(len(s)) {
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
  Str* Value();  // similar to index_()

 private:
  Str* s_;
  int i_;
  int len_;

  DISALLOW_COPY_AND_ASSIGN(StrIter)
};

bool maybe_str_equals(Str* left, Str* right);

extern Str* kEmptyString;

// GlobalStr notes:
// - sizeof("foo") == 4, for the NUL terminator.
// - gc_heap_test.cc has a static_assert that GlobalStr matches Str.  We don't
// put it here because it triggers -Winvalid-offsetof

template <int N>
class GlobalStr {
  // A template type with the same layout as Str with length N-1 (which needs a
  // buffer of size N).  For initializing global constant instances.
 public:
  int len_;
  int hash_value_;
  const char data_[N];

  DISALLOW_COPY_AND_ASSIGN(GlobalStr)
};

// This macro is a workaround for the fact that it's impossible to have a
// a constexpr initializer for char[N].  The "String Literals as Non-Type
// Template Parameters" feature of C++ 20 would have done it, but it's not
// there.
//
// https://old.reddit.com/r/cpp_questions/comments/j0khh6/how_to_constexpr_initialize_class_member_thats/
// https://stackoverflow.com/questions/10422487/how-can-i-initialize-char-arrays-in-a-constructor
//
// TODO: Can we hash values at compile time so they can be in the intern table?

#define GLOBAL_STR(name, val)                                     \
  GcGlobal<GlobalStr<sizeof(val)>> _##name = {                    \
      ObjHeader::Global(TypeTag::Str),                            \
      {.len_ = sizeof(val) - 1, .hash_value_ = 0, .data_ = val}}; \
  Str* name = reinterpret_cast<Str*>(&_##name.obj);

#endif  // MYCPP_GC_STR_H
