#ifndef GC_TAG_H
#define GC_TAG_H

// Obj::heap_tag_ values.  They're odd numbers to distinguish them from vtable
// pointers.
//
// NOTE(Jesse): Changed to an enum because namespaces can't be typedef'd.
// ie can't be included using the 'using' keyword
//
enum Tag {
  Forwarded = 1,  // For the Cheney algorithm.
  Global = 3,     // Neither copy nor scan.
  Opaque = 5,     // Copy but don't scan.  List<int> and Str
  FixedSize = 7,  // Fixed size headers: consult field_mask_
  Scanned = 9,    // Copy AND scan for non-NULL pointers.
};

#endif  // GC_TAG_H
