#ifndef GC_OBJ_H
#define GC_OBJ_H

enum Tag {
  Global = 0,  // Don't mark or sweep.  (Don't copy or scan)
  Opaque = 1,  // Mark and sweep, e.g. List<int>, Str.  (Copy but don't scan.)
  FixedSize = 2,  // Consult field_mask for children
  Scanned = 3,    // Scan a contiguous range of children

  Forwarded = 4,  // For the Cheney algorithm.  It needs 3 bits instead of 2!
};

// This "enum" starts from the end of the valid type_tag range.
// asdl/gen_cpp.py starts from 1 for variants, or 64 for shared variants.
namespace TypeTag {
const int OtherClass = 127;  // non-ASDL class
const int Str = 126;
const int Slab = 125;
const int Tuple = 124;
};  // namespace TypeTag

const int kIsHeader = 1;

const uint16_t kZeroMask = 0;  // for types with no pointers

// no obj_len computed for global List/Slab/Dict
const int kNoObjLen = 0x0badbeef;

// TODO: ./configure could detect big or little endian, and then flip the
// fields in ObjHeader?
//
// https://stackoverflow.com/questions/2100331/c-macro-definition-to-determine-big-endian-or-little-endian-machine
//
// Because we want to do (obj->heap_tag & 1 == 0) to distinguish it from
// vtable pointer.  We assume low bits of a pointer are 0 but not high bits.

// The first member of every GC-managed object is 'ObjHeader header_'.
// (There's no inheritance!)
struct ObjHeader {
  unsigned is_header : 1;  // To distinguish from vtable pointer
                           // Overlaps with RawObject::points_to_header
  unsigned heap_tag : 7;   // Tag::Opaque, etc.
  uint8_t type_tag;        // TypeTag, ASDL variant / shared variant
  uint16_t field_mask;     // For some user-defined classes, so max 16 fields
  uint32_t obj_len;        // Mark-sweep: derive Str length, Slab length
                           // Cheney: number of bytes to copy
};

// A RawObject* is like a void* -- it can point to any C++ object.  The object
// may start with either ObjHeader, or vtable pointer then an ObjHeader.
struct RawObject {
  unsigned points_to_header : 1;
  unsigned pad : 31;
};

// Used by hand-written and generated classes
#define GC_CLASS_FIXED(header_, field_mask, obj_len)                    \
  header_ {                                                             \
    kIsHeader, Tag::FixedSize, TypeTag::OtherClass, field_mask, obj_len \
  }

// Used by mycpp and frontend/flag_gen.py.  TODO: Sort fields and use
// Tag::Scanned.
#define GC_CLASS(header_, heap_tag, field_mask, obj_len)          \
  header_ {                                                       \
    kIsHeader, heap_tag, TypeTag::OtherClass, field_mask, obj_len \
  }

// Used by ASDL.  TODO: Sort fields and use Tag::Scanned
#define GC_ASDL_CLASS(header_, type_tag, field_mask, obj_len) \
  header_ {                                                   \
    kIsHeader, Tag::FixedSize, type_tag, field_mask, obj_len  \
  }

#define GC_STR(header_)                                        \
  header_ {                                                    \
    kIsHeader, Tag::Opaque, TypeTag::Str, kZeroMask, kNoObjLen \
  }

#define GC_SLAB(header_, heap_tag, obj_len)                \
  header_ {                                                \
    kIsHeader, heap_tag, TypeTag::Slab, kZeroMask, obj_len \
  }

#define GC_TUPLE(header_, field_mask, obj_len)                     \
  header_ {                                                        \
    kIsHeader, Tag::FixedSize, TypeTag::Tuple, field_mask, obj_len \
  }

// TODO: could omit this in BUMP_LEAK mode
#define GC_OBJ(var_name) ObjHeader var_name

//
// Compile-time computation of GC field masks.
//

class _DummyObj {  // For maskbit()
 public:
  ObjHeader header_;
  int first_field_;
};

// maskbit(field_offset) returns a bit in mask that you can bitwise-or (|) with
// other bits.
//
// - Note that we only call maskbit() on offsets of pointer fields, which must
//   be POINTER-ALIGNED.
// - _DummyObj is used in case ObjHeader requires padding, then
//   sizeof(ObjHeader) != offsetof(_DummyObj, first_field_)

constexpr int maskbit(int offset) {
  return 1 << ((offset - offsetof(_DummyObj, first_field_)) / sizeof(void*));
}

class _DummyObj_v {  // For maskbit_v()
 public:
  void* vtable;  // how the compiler does dynamic dispatch
  ObjHeader header_;
  int first_field_;
};

// maskbit_v(field_offset) is like maskbit(), but accounts for the vtable
// pointer.

constexpr int maskbit_v(int offset) {
  return 1 << ((offset - offsetof(_DummyObj_v, first_field_)) / sizeof(void*));
}

inline ObjHeader* FindObjHeader(RawObject* obj) {
  if (obj->points_to_header) {
    return reinterpret_cast<ObjHeader*>(obj);
  } else {
    // We saw a vtable pointer, so return the ObjHeader* header that
    // immediately follows.
    return reinterpret_cast<ObjHeader*>(reinterpret_cast<char*>(obj) +
                                        sizeof(void*));
  }
}

// The "homogeneous" layout of objects with Tag::FixedSize.  LayoutFixed is for
// casting; it isn't a real type.

class LayoutFixed {
 public:
  ObjHeader header_;
  // only the entries denoted in field_mask will be valid
  RawObject* children_[16];
};

#endif
