// gc_test.cc

#include "gc_heap.h"
#include "greatest.h"

// problem: shouldn't include mylib!
// ASDL depends on mycpp
// #include "runtime.h"

#include "typed_demo_asdl.gc.h"

using gc_heap::NewStr;
using gc_heap::Alloc;
using gc_heap::Local;
// using hnode_asdl::hnode_str;

using typed_demo_asdl::word;
using typed_demo_asdl::bool_expr__Binary;

TEST pretty_print_test() {
  // typed_demo.asdl

  // auto o = op_id_e::Plus;
  // Note: this is NOT prevented at compile time, even though it's illegal.
  // left and right are not optional.
  // auto b = new bool_expr__LogicalBinary(o, nullptr, nullptr);

  Local<word> w1 = Alloc<word>(NewStr("left"));
  Local<word> w2 = Alloc<word>(NewStr("right"));
  Local<bool_expr__Binary> b = Alloc<bool_expr__Binary>(w1, w2);

  //
  log("sizeof b = %d", sizeof b);
  log("");
  /*
  hnode_t* t1 = b->AbbreviatedTree();
  ASSERT(strcmp("hnode.Record", hnode_str(t1->tag_())) == 0);
  */

  /*
  auto f = mylib::Stdout();
  auto ast_f = new format::TextOutput(f);
  format::PrintTree(t1, ast_f);
  */

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gc_heap::gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(pretty_print_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
