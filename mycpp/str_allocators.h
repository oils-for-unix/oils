#ifndef STR_ALLOCATORS_H
#define STR_ALLOCATORS_H

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
  #ifdef LEAKY_BINDINGS
    #define ALLOCATE(byte_count) calloc(byte_count, 1)
  #else
    #define ALLOCATE(byte_count) gHeap.Allocate(byte_count);
  #endif
#endif

inline Str* AllocStr(int len) {
  int obj_len = kStrHeaderSize + len + 1;
  void* place = ALLOCATE(obj_len);
  auto s = new (place) Str();
  s->SetObjLen(obj_len);
  return s;
}

// Like AllocStr, but allocate more than you need, e.g. for snprintf() to write
// into.  CALLER IS RESPONSIBLE for calling s->SetObjLenFromStrLen() afterward!
inline Str* OverAllocatedStr(int len) {
  int obj_len = kStrHeaderSize + len + 1;  // NUL terminator
  void* place = ALLOCATE(obj_len);
  auto s = new (place) Str();
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

#endif
