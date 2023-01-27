#include "_gen/core/runtime.asdl.h"  // cell, etc
#include "_gen/frontend/syntax.asdl.h"
#include "vendor/greatest.h"

TEST sizeof_syntax() {
  // 40 bytes (after merging with line_span January 2023)
  // - Get rid of 'string val' 
  // - Replace 'int line_id' with SourceLine
  // - Maybe recompute length on demand
  log("sizeof(Token) = %d", sizeof(syntax_asdl::Token));
  log("alignof(Token) = %d", alignof(syntax_asdl::Token));
  log("alignof(Token*) = %d", alignof(syntax_asdl::Token*));

  // Reordered to be 16 bytes
  log("sizeof(cell) = %d", sizeof(runtime_asdl::cell));

  // 24 bytes: std::vector
  log("sizeof(List<int>) = %d", sizeof(List<int>));
  log("sizeof(List<Str*>) = %d", sizeof(List<Str*>));

  log("sizeof(Slab<int>) = %d", sizeof(Slab<int>));
  log("sizeof(Slab<Str*>) = %d", sizeof(Slab<Str*>));
  // Right after object header
  log("kSlabHeaderSize = %d", kSlabHeaderSize);

  // Unlike Python, this is -1, not 255!
  int mod = -1 % 256;
  log("mod = %d", mod);

  log("alignof(bool) = %d", alignof(bool));
  log("alignof(int) = %d", alignof(int));
  log("alignof(float) = %d", alignof(float));

  log("sizeof(Str) = %d", sizeof(Str));
  log("alignof(Str) = %d", alignof(Str));

  log("sizeof(Str*) = %d", sizeof(Str*));
  log("alignof(Str*) = %d", alignof(Str*));

  log("alignof(max_align_t) = %d", alignof(max_align_t));

  PASS();
}

// Doesn't really test anything
TEST sizeof_core_types() {
  log("");

  // 8 byte header
  log("sizeof(ObjHeader) = %d", sizeof(ObjHeader));
  // 8 + 128 possible entries
  // log("sizeof(LayoutFixed) = %d", sizeof(LayoutFixed));

  // 24 = 4 + (4 + 4 + 4) + 8
  // Feels like a small string optimization here would be nice.
  log("sizeof(Str) = %d", sizeof(Str));
  // 16 = 4 + pad4 + 8
  log("sizeof(List) = %d", sizeof(List<int>));
  // 32 = 4 + pad4 + 8 + 8 + 8
  log("sizeof(Dict) = %d", sizeof(Dict<int, int>));

#ifndef MARK_SWEEP
  int min_obj_size = sizeof(LayoutForwarded);
  int short_str_size = aligned(kStrHeaderSize + 1);

  log("kStrHeaderSize = %d", kStrHeaderSize);
  log("aligned(kStrHeaderSize + 1) = %d", short_str_size);
  log("sizeof(LayoutForwarded) = %d", min_obj_size);

  ASSERT(min_obj_size <= short_str_size);
#endif

#if 0
  char* p = static_cast<char*>(gHeap.Allocate(17));
  char* q = static_cast<char*>(gHeap.Allocate(9));
  log("p = %p", p);
  log("q = %p", q);
#endif

  // Str = 16 and List = 24.
  // Rejected ideas about slicing:
  //
  // - Use data[len] == '\0' as OWNING and data[len] != '\0' as a slice?
  //   It doesn't work because s[1:] would always have that problem
  //
  // - s->data == (void*)(s + 1)
  //   Owning string has the data RIGHT AFTER?
  //   Maybe works? but probably a bad idea because of GLOBAL Str instances.

  log("");
  log("sizeof(Str) = %zu", sizeof(Str));
  log("sizeof(List<int>) = %zu", sizeof(List<int>));
  log("sizeof(Dict<int, Str*>) = %zu", sizeof(Dict<int, Str*>));
  log("sizeof(Tuple2<int, int>) = %zu", sizeof(Tuple2<int, int>));
  log("sizeof(Tuple2<Str*, Str*>) = %zu", sizeof(Tuple2<Str*, Str*>));
  log("sizeof(Tuple3<int, int, int>) = %zu", sizeof(Tuple3<int, int, int>));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(sizeof_syntax);
  RUN_TEST(sizeof_core_types);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
