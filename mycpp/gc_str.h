#ifndef STR_TYPES_H
#define STR_TYPES_H

#ifdef OLDSTL_BINDINGS

template <typename T>
class List;

#else



#endif



class Str : public Obj {
 public:

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

inline int len(const Str* s) {
  // NOTE(Jesse): Not sure if 0-length strings should be allowed, but we
  // currently don't hit this assertion, so I would think not?
  assert(s->obj_len_ >= kStrHeaderSize - 1);

  return s->obj_len_ - kStrHeaderSize - 1;
}

inline void Str::SetObjLenFromStrLen(int str_len) {
  obj_len_ = kStrHeaderSize + str_len + 1;
  /* assert(len(this) == str_len); */
}

// Notes:
// - sizeof("foo") == 4, for the NUL terminator.
// - gc_heap_test.cc has a static_assert that GlobalStr matches Str.  We don't
// put it here because it triggers -Winvalid-offsetof

//
// String "Constructors".  We need these because of the "flexible array"
// pattern.  I don't think "new Str()" can do that, and placement new would
// require mycpp to generate 2 statements everywhere.
//

#ifndef ALLOCATE
  #ifdef OLDSTL_BINDINGS
    #define ALLOCATE(byte_count) calloc(byte_count, 1)
  #else
    #define ALLOCATE(byte_count) gHeap.Allocate(byte_count);
  #endif
#endif

inline void InitObj(void* buf, uint8_t heap_tag, uint8_t type_tag, uint16_t field_mask, uint32_t obj_len)
{
  Obj *obj = static_cast<Obj*>(buf);
  obj->heap_tag_ = heap_tag;
  obj->type_tag_ = type_tag;
  obj->field_mask_ = field_mask;
  obj->obj_len_ = obj_len;
}

inline int ObjLenFromStrLen(int len)
{
  return kStrHeaderSize + len + 1;
}

inline Str* InitStr(void* buf, int str_len, int obj_len) {
  InitObj(buf, Tag::Opaque, 0, kZeroMask, obj_len);
  return static_cast<Str*>(buf);
}

inline Str* AllocStr(int str_len) {
  int obj_len = ObjLenFromStrLen(str_len);
  void* place = ALLOCATE(obj_len);
  Str* result = InitStr(place, str_len, obj_len);
  return result;
}

// NOTE(Jesse): This API is safe, but instructive for the reader of the calling
// code that the string is used as a buffer to incrementally copy into.  Could
// be a good idea to audit call-sites of this and change to BoundedBuffer ..?
inline Str* OverAllocatedStr(int len) {
  Str* s = AllocStr(len);
  return s;
}

#undef ALLOCATE

inline Str* StrFromC(const char* data, int len) {
  Str* s = AllocStr(len);
  memcpy(s->data_, data, len);
  assert(s->data_[len] == '\0');  // should be true because Heap was zeroed

  return s;
}

inline Str* StrFromC(const char* data) {
  return StrFromC(data, strlen(data));
}

inline Str* CopyBufferIntoNewStr(char* buf) {
  Str* s = StrFromC(buf);
  return s;
}

inline Str* CopyBufferIntoNewStr(char* buf, unsigned int buf_len) {
  Str* s = StrFromC(buf, buf_len);
  return s;
}

#endif // STR_TYPES_H
