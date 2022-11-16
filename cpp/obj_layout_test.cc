#include "_gen/core/runtime.asdl.h"  // cell, etc
#include "_gen/frontend/syntax.asdl.h"
#include "vendor/greatest.h"

TEST sizeof_syntax() {
  // Without sed hack, it's 24 bytes because we have tag (2), id (4), val,
  // span_id.
  // Now 16 bytes.
  log("sizeof(Token) = %d", sizeof(syntax_asdl::Token));
  log("alignof(Token) = %d", alignof(syntax_asdl::Token));
  log("alignof(Token*) = %d", alignof(syntax_asdl::Token*));

  // Without sed hack, it's 12 bytes for tag (2) id (4) and span_id (4).
  // Now 8 bytes.
  log("sizeof(speck) = %d", sizeof(syntax_asdl::speck));

  // 16 bytes: 2 byte tag + 3 integer fields
  log("sizeof(line_span) = %d", sizeof(syntax_asdl::line_span));

  // Reordered to be 16 bytes
  log("sizeof(cell) = %d", sizeof(runtime_asdl::cell));

  // 24 bytes: std::vector
  log("sizeof(List<int>) = %d", sizeof(List<int>));
  log("sizeof(List<Str*>) = %d", sizeof(List<Str*>));

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

  // 24 = 4 + (4 + 4 + 4) + 8
  // Feels like a small string optimization here would be nice.
  log("sizeof(Str) = %d", sizeof(Str));
  // 16 = 4 + pad4 + 8
  log("sizeof(List) = %d", sizeof(List<int>));
  // 32 = 4 + pad4 + 8 + 8 + 8
  log("sizeof(Dict) = %d", sizeof(Dict<int, int>));

  // 8 byte sheader
  log("sizeof(Obj) = %d", sizeof(Obj));
  // 8 + 128 possible entries
  // log("sizeof(LayoutFixed) = %d", sizeof(LayoutFixed));

  /* log("sizeof(Heap) = %d", sizeof(Heap)); */

#ifndef MARK_SWEEP
  int min_obj_size = sizeof(LayoutForwarded);
  int short_str_size = aligned(kStrHeaderSize + 1);

  log("kStrHeaderSize = %d", kStrHeaderSize);
  log("aligned(kStrHeaderSize + 1) = %d", short_str_size);
  log("sizeof(LayoutForwarded) = %d", min_obj_size);

  ASSERT(min_obj_size <= short_str_size);
#endif

  char* p = static_cast<char*>(gHeap.Allocate(17));
  char* q = static_cast<char*>(gHeap.Allocate(9));
  log("p = %p", p);
  log("q = %p", q);

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
