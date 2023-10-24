#ifndef MYCPP_GC_OBJ_H
#define MYCPP_GC_OBJ_H

#include <stdint.h>  // uint8_t

#include "mycpp/common.h"

namespace HeapTag {
const int Global = 0;     // Don't mark or sweep.
const int Opaque = 1;     // e.g. List<int>, BigStr
                          // Mark and sweep, but don't trace children
const int FixedSize = 2;  // Consult field_mask for children
const int Scanned = 3;    // Scan a contiguous range of children
};                        // namespace HeapTag

// These tags are mainly for debugging.  Oils is a statically typed program, so
// we don't need runtime types in general.
// This "enum" starts from the end of the valid type_tag range.
// asdl/gen_cpp.py starts from 1 for variants, or 64 for shared variants.
namespace TypeTag {
const int OtherClass = 127;  // non-ASDL class
const int BigStr = 126;      // asserted in dynamic StrFormat()
const int Slab = 125;
const int Tuple = 124;
const int List = 123;
const int Dict = 122;
};  // namespace TypeTag

const int kNotInPool = 0;
const int kInPool = 1;

const unsigned kZeroMask = 0;  // for types with no pointers

const int kMaxObjId = (1 << 28) - 1;  // 28 bits means 512 Mi objects per pool
const int kIsGlobal = kMaxObjId;      // for debugging, not strictly needed

const int kUndefinedId = 0;  // Uninitialized object ID

// Every GC-managed object is preceded in memory by an ObjHeader.
// TODO: ./configure could detect endian-ness, and reorder the fields in
// ObjHeader.  See mycpp/demo/gc_header.cc.
struct ObjHeader {
  unsigned type_tag : 8;  // TypeTag, ASDL variant / shared variant
  // Depending on heap_tag, up to 24 fields or 2**24 = 16 Mi pointers to scan
  unsigned u_mask_npointers : 24;

  unsigned heap_tag : 2;  // HeapTag::Opaque, etc.
  unsigned pool_id : 2;   // 0 for malloc(), or 1 2 3 for fixed sized pools
  unsigned obj_id : 28;   // 1 Gi unique objects

  // Returns the address of the GC managed object associated with this header.
  // Note: this relies on there being no padding between the header and the
  // object. See Alloc<T>() and GcGlobal<T> for relevant static_assert()s.
  void* ObjectAddress() {
    return reinterpret_cast<void*>(reinterpret_cast<char*>(this) +
                                   sizeof(ObjHeader));
  }

  // Returns the header for the given GC managed object.
  // Note: this relies on there being no padding between the header and the
  // object. See Alloc<T>() and GcGlobal<T> for relevant static_assert()s.
  static ObjHeader* FromObject(const void* obj) {
    return reinterpret_cast<ObjHeader*>(
        static_cast<char*>(const_cast<void*>(obj)) - sizeof(ObjHeader));
  }

  // Used by hand-written and generated classes
  static constexpr ObjHeader ClassFixed(uint32_t field_mask, uint32_t obj_len) {
    return {TypeTag::OtherClass, field_mask, HeapTag::FixedSize, kNotInPool,
            kUndefinedId};
  }

  // Classes with no inheritance (e.g. used by mycpp)
  static constexpr ObjHeader ClassScanned(uint32_t num_pointers,
                                          uint32_t obj_len) {
    return {TypeTag::OtherClass, num_pointers, HeapTag::Scanned, kNotInPool,
            kUndefinedId};
  }

  // Used by frontend/flag_gen.py.  TODO: Sort fields and use GC_CLASS_SCANNED
  static constexpr ObjHeader Class(uint8_t heap_tag, uint32_t field_mask,
                                   uint32_t obj_len) {
    return {TypeTag::OtherClass, field_mask, heap_tag, kNotInPool,
            kUndefinedId};
  }

  // Used by ASDL.
  static constexpr ObjHeader AsdlClass(uint8_t type_tag,
                                       uint32_t num_pointers) {
    return {type_tag, num_pointers, HeapTag::Scanned, kNotInPool, kUndefinedId};
  }

  static constexpr ObjHeader BigStr() {
    return {TypeTag::BigStr, kZeroMask, HeapTag::Opaque, kNotInPool,
            kUndefinedId};
  }

  static constexpr ObjHeader Slab(uint8_t heap_tag, uint32_t num_pointers) {
    return {TypeTag::Slab, num_pointers, heap_tag, kNotInPool, kUndefinedId};
  }

  static constexpr ObjHeader Tuple(uint32_t field_mask, uint32_t obj_len) {
    return {TypeTag::Tuple, field_mask, HeapTag::FixedSize, kNotInPool,
            kUndefinedId};
  }

  // Used by GLOBAL_STR, GLOBAL_LIST, GLOBAL_DICT
  static constexpr ObjHeader Global(uint8_t type_tag) {
    return {type_tag, kZeroMask, HeapTag::Global, kNotInPool, kIsGlobal};
  }
};

#define FIELD_MASK(header) (header).u_mask_npointers
#define NUM_POINTERS(header) (header).u_mask_npointers

// A RawObject* is like a void*. We use it to represent GC managed objects.
struct RawObject;

//
// Compile-time computation of GC field masks.
//

// maskbit(field_offset) returns a bit in mask that you can bitwise-or (|) with
// other bits.
//
// - Note that we only call maskbit() on offsets of pointer fields, which must
//   be POINTER-ALIGNED.

constexpr int maskbit(size_t offset) {
  return 1 << (offset / sizeof(void*));
}

// A wrapper for a GC object and its header. For creating global GC objects,
// like GlobalStr.
// TODO: Make this more ergonomic by automatically initializing header
// with T::obj_header() and providing a forwarding constructor for obj.
template <typename T>
class GcGlobalImpl {
 public:
  ObjHeader header;
  T obj;

  // This class only exists to write the static_assert. If you try to put the
  // static_assert directly in the outer class you get a compiler error that
  // taking the offsets is an 'invalid use of incomplete type'. Doing it this
  // way means the type gets completed before the assert.
  struct Internal {
    using type = GcGlobalImpl<T>;
    static_assert(offsetof(type, obj) - sizeof(ObjHeader) ==
                      offsetof(type, header),
                  "ObjHeader doesn't fit");
  };

  DISALLOW_COPY_AND_ASSIGN(GcGlobalImpl);
};

// Refer to `Internal::type` to force Internal to be instantiated.
template <typename T>
using GcGlobal = typename GcGlobalImpl<T>::Internal::type;

// The "homogeneous" layout of objects with HeapTag::FixedSize.  LayoutFixed is
// for casting; it isn't a real type.

// TODO: we could determine the max of all objects statically!
const int kFieldMaskBits = 24;

struct LayoutFixed {
  // only the entries denoted in field_mask will be valid
  RawObject* children_[kFieldMaskBits];
};

#endif  // MYCPP_GC_OBJ_H
