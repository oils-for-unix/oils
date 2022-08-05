#ifndef STR_TYPES_H
#define STR_TYPES_H

using gc_heap::kZeroMask;

class Str : public gc_heap::Obj {
 public:
  // Don't call this directly.  Call AllocStr() instead, which calls this.
  explicit Str() : Obj(Tag::Opaque, kZeroMask, 0) {
    // log("GC Str()");
  }

  char* data() {
    return data_;
  };

  void SetObjLenFromStrLen(int str_len);

  Str* index_(int i);

  int find(Str* needle, int pos = 0);
  int rfind(Str* needle);

  Str* slice(int begin);
  Str* slice(int begin, int end);

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
  int hash_value_;
  char data_[1];  // flexible array

 private:
  int _strip_left_pos();
  int _strip_right_pos();

  DISALLOW_COPY_AND_ASSIGN(Str)
};

constexpr int kStrHeaderSize = offsetof(Str, data_);

inline void Str::SetObjLenFromStrLen(int str_len) {
  obj_len_ = kStrHeaderSize + str_len + 1;  // NUL terminator
}

#endif // STR_TYPES_H
