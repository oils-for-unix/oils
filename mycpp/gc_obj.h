#ifndef GC_OBJ_H
#define GC_OBJ_H

// Obj::heap_tag_ values.  They're odd numbers to distinguish them from vtable
// pointers.
//
enum Tag {
  Forwarded = 1,  // For the Cheney algorithm.
  Global = 3,     // Neither copy nor scan.
  Opaque = 5,     // Copy but don't scan.  List<int> and Str
  FixedSize = 7,  // Fixed size headers: consult field_mask_
  Scanned = 9,    // Copy AND scan for non-NULL pointers.
};

const int kZeroMask = 0;  // for types with no pointers
// no obj_len_ computed for global List/Slab/Dict
const int kNoObjLen = 0x0badbeef;

// Why do we need this macro instead of using inheritance?
// - Because ASDL uses multiple inheritance for first class variants, but we
//   don't want multiple IMPLEMENTATION inheritance.  Instead we just generate
//   compatible layouts.
// - Similarly, GlobalStr is layout-compatible with Str.  It can't inherit from
//   Obj like Str, because of the constexpr issue with char[N].

// heap_tag_: one of Tag::
// type_tag_: ASDL tag (variant)
// field_mask_: for fixed length records, so max 16 fields
// obj_len_: number of bytes to copy
//   TODO: with a limitation of ~15 fields, we can encode obj_len_ in
//   field_mask_, and save space on many ASDL types.
//   And we can sort integers BEFORE pointers.

// TODO: ./configure could detect big or little endian, and then flip the
// fields in OBJ_HEADER?
//
// https://stackoverflow.com/questions/2100331/c-macro-definition-to-determine-big-endian-or-little-endian-machine
//
// Because we want to do (obj->heap_tag_ & 1 == 0) to distinguish it from
// vtable pointer.  We assume low bits of a pointer are 0 but not high bits.

#define OBJ_HEADER()    \
  uint8_t heap_tag_;    \
  uint8_t type_tag_;    \
  uint16_t field_mask_; \
  uint32_t obj_len_;

class Obj {
  // The unit of garbage collection.  It has a header describing how to find
  // the pointers within it.
  //
  // Note: Sorting ASDL fields by (non-pointer, pointer) is a good idea, but it
  // breaks down because mycpp has inheritance.  Could do this later.

 public:
  // Note: ASDL types are layout-compatible with Obj, but don't actually
  // inherit from it because of the 'multiple inheritance of implementation'
  // issue.  So they don't call this constructor.
  constexpr Obj(uint8_t heap_tag, uint16_t field_mask, int obj_len)
      : heap_tag_(heap_tag),
        type_tag_(0),
        field_mask_(field_mask),
        obj_len_(obj_len) {
  }

  void SetObjLen(int obj_len) {
    obj_len_ = obj_len;
  }

  OBJ_HEADER()

  DISALLOW_COPY_AND_ASSIGN(Obj)
};

//
// Compile-time computation of GC field masks.
//

class _DummyObj {  // For maskbit()
 public:
  OBJ_HEADER()
  int first_field_;
};

// maskbit(field_offset) returns a bit in mask that you can bitwise-or (|) with
// other bits.
//
// - Note that we only call maskbit() on offsets of pointer fields, which must
//   be POINTER-ALIGNED.
// - _DummyObj is used in case OBJ_HEADER() requires padding, then
//   sizeof(Obj) != offsetof(_DummyObj, first_field_)

constexpr int maskbit(int offset) {
  return 1 << ((offset - offsetof(_DummyObj, first_field_)) / sizeof(void*));
}

class _DummyObj_v {  // For maskbit_v()
 public:
  void* vtable;  // how the compiler does dynamic dispatch
  OBJ_HEADER()
  int first_field_;
};

// maskbit_v(field_offset) is like maskbit(), but accounts for the vtable
// pointer.

constexpr int maskbit_v(int offset) {
  return 1 << ((offset - offsetof(_DummyObj_v, first_field_)) / sizeof(void*));
}

inline Obj* ObjHeader(Obj* obj) {
  // If we see a vtable pointer, return the Obj* header immediately following.
  // Otherwise just return Obj itself.
  return (obj->heap_tag_ & 0x1) == 0
             ? reinterpret_cast<Obj*>(reinterpret_cast<char*>(obj) +
                                      sizeof(void*))
             : obj;
}

#endif
