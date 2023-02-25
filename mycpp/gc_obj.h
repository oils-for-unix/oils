#ifndef MYCPP_GC_OBJ_H
#define MYCPP_GC_OBJ_H

#include <stdint.h>  // uint8_t

namespace HeapTag {
const int Global = 0;     // Don't mark or sweep.
                          // Cheney: Don't copy or scan.
const int Opaque = 1;     // e.g. List<int>, Str
                          // Mark and sweep, but don't trace children
                          // Cheney: Copy, but don't scan.
const int FixedSize = 2;  // Consult field_mask for children
const int Scanned = 3;    // Scan a contiguous range of children

const int Forwarded = 4;  // For the Cheney algorithm.
};                        // namespace HeapTag

// These tags are mainly for debugging.  Oil is a statically typed
// program, so we don't need runtime types in general.
// This "enum" starts from the end of the valid type_tag range.
// asdl/gen_cpp.py starts from 1 for variants, or 64 for shared variants.
namespace TypeTag {
const int OtherClass = 127;  // non-ASDL class
const int Str = 126;         // asserted in dynamic StrFormat()
const int Slab = 125;
const int Tuple = 124;
};  // namespace TypeTag

const int kIsHeader = 1;  // for is_header bit

const unsigned kZeroMask = 0;  // for types with no pointers

const int kMaxObjId = (1 << 30) - 1;  // 30 bit object ID
const int kIsGlobal = kMaxObjId;      // for debugging, not strictly needed

const int kUndefinedId = 0;  // Unitialized object ID

// The first member of every GC-managed object is 'ObjHeader header_'.
// (There's no inheritance!)
struct ObjHeader {
  unsigned is_header : 1;  // To distinguish from vtable pointer
                           // Overlaps with RawObject::points_to_header
  unsigned type_tag : 7;   // TypeTag, ASDL variant / shared variant
#if defined(MARK_SWEEP) || defined(BUMP_LEAK)
  // Depending on heap_tag, up to 24 fields or 2**24 = 16 Mi pointers to scan
  unsigned u_mask_npointers : 24;
#else
  unsigned field_mask : 24;  // Cheney needs field_maks AND obj_len
#endif

#if defined(MARK_SWEEP) || defined(BUMP_LEAK)
  unsigned heap_tag : 2;  // HeapTag::Opaque, etc.
  unsigned obj_id : 30;   // 1 Gi unique objects
#else
  unsigned heap_tag : 3;     // Cheney also needs HeapTag::Forwarded
  unsigned obj_len : 29;     // Cheney: number of bytes to copy
#endif

  // Used by hand-written and generated classes
  static constexpr ObjHeader ClassFixed(uint16_t field_mask, uint32_t obj_len) {
    return {kIsHeader, TypeTag::OtherClass, field_mask, HeapTag::FixedSize,
            kUndefinedId};
  }

  // Classes with no inheritance (e.g. used by mycpp)
  static constexpr ObjHeader ClassScanned(uint32_t num_pointers,
                                          uint32_t obj_len) {
    return {kIsHeader, TypeTag::OtherClass, num_pointers, HeapTag::Scanned,
            kUndefinedId};
  }

  // Used by frontend/flag_gen.py.  TODO: Sort fields and use GC_CLASS_SCANNED
  static constexpr ObjHeader Class(uint8_t heap_tag, uint16_t field_mask,
                                   uint32_t obj_len) {
    return {kIsHeader, TypeTag::OtherClass, field_mask, heap_tag, kUndefinedId};
  }

  // Used by ASDL.
  static constexpr ObjHeader AsdlClass(uint8_t type_tag,
                                       uint32_t num_pointers) {
    return {kIsHeader, type_tag, num_pointers, HeapTag::Scanned, kUndefinedId};
  }

  static constexpr ObjHeader Str() {
    return {kIsHeader, TypeTag::Str, kZeroMask, HeapTag::Opaque, kUndefinedId};
  }

  static constexpr ObjHeader Slab(uint8_t heap_tag, uint32_t num_pointers) {
    return {kIsHeader, TypeTag::Slab, num_pointers, heap_tag, kUndefinedId};
  }

  static constexpr ObjHeader Tuple(uint16_t field_mask, uint32_t obj_len) {
    return {kIsHeader, TypeTag::Tuple, field_mask, HeapTag::FixedSize,
            kUndefinedId};
  }
};

// TODO: we could determine the max of all objects statically!
const int kFieldMaskBits = 16;

#if defined(MARK_SWEEP) || defined(BUMP_LEAK)
  #define FIELD_MASK(header) (header).u_mask_npointers
  #define NUM_POINTERS(header) (header).u_mask_npointers

#else
  #define FIELD_MASK(header) (header).field_mask
                             // TODO: derive from obj_len
  #define NUM_POINTERS(header) \
    ((header.obj_len - kSlabHeaderSize) / sizeof(void*))
#endif

// A RawObject* is like a void* -- it can point to any C++ object.  The object
// may start with either ObjHeader, or vtable pointer then an ObjHeader.
struct RawObject {
  unsigned points_to_header : 1;  // same as ObjHeader::is_header
  unsigned pad : 31;
};

// TODO: ./configure could detect endian-ness, and reorder the fields in
// ObjHeader.  See mycpp/demo/gc_header.cc.

// Used by hand-written and generated classes
#define GC_CLASS_FIXED(header_, field_mask, obj_len)                \
  header_ {                                                         \
    kIsHeader, TypeTag::OtherClass, field_mask, HeapTag::FixedSize, \
        kUndefinedId                                                \
  }

// Classes with no inheritance (e.g. used by mycpp)
#define GC_CLASS_SCANNED(header_, num_pointers, obj_len)            \
  header_ {                                                         \
    kIsHeader, TypeTag::OtherClass, num_pointers, HeapTag::Scanned, \
        kUndefinedId                                                \
  }

// Used by frontend/flag_gen.py.  TODO: Sort fields and use GC_CLASS_SCANNED
#define GC_CLASS(header_, heap_tag, field_mask, obj_len)               \
  header_ {                                                            \
    kIsHeader, TypeTag::OtherClass, field_mask, heap_tag, kUndefinedId \
  }

// Used by ASDL.
#define GC_ASDL_CLASS(header_, type_tag, num_pointers)                \
  header_ {                                                           \
    kIsHeader, type_tag, num_pointers, HeapTag::Scanned, kUndefinedId \
  }

#define GC_STR(header_)                                               \
  header_ {                                                           \
    kIsHeader, TypeTag::Str, kZeroMask, HeapTag::Opaque, kUndefinedId \
  }

#define GC_SLAB(header_, heap_tag, num_pointers)                   \
  header_ {                                                        \
    kIsHeader, TypeTag::Slab, num_pointers, heap_tag, kUndefinedId \
  }

#define GC_TUPLE(header_, field_mask, obj_len)                              \
  header_ {                                                                 \
    kIsHeader, TypeTag::Tuple, field_mask, HeapTag::FixedSize, kUndefinedId \
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

// The "homogeneous" layout of objects with HeapTag::FixedSize.  LayoutFixed is
// for casting; it isn't a real type.

class LayoutFixed {
 public:
  ObjHeader header_;
  // only the entries denoted in field_mask will be valid
  RawObject* children_[kFieldMaskBits];
};

#endif  // MYCPP_GC_OBJ_H
