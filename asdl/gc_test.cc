// asdl/gc_test.cc

#include "_build/cpp/hnode_asdl.gc.h"
#include "asdl/runtime.gc.h"
#include "cpp/greatest.h"
#include "mycpp/gc_heap.h"
#include "mycpp/mylib2.h"

#include "typed_demo_asdl.gc.h"

using gc_heap::Alloc;
using gc_heap::NewStr;

using hnode_asdl::hnode_t;
using hnode_asdl::hnode_str;

using typed_demo_asdl::bool_expr__Binary;
using typed_demo_asdl::word;

TEST pretty_print_test() {
  auto w1 = Alloc<word>(NewStr("left"));
  auto w2 = Alloc<word>(NewStr("right"));
  auto b = Alloc<bool_expr__Binary>(w1, w2);

#if 0
  log("sizeof b = %d", sizeof b);
  log("");
#endif

  // Note: this segfaults with 1000 iterations, because it hit GC.
  // TODO: GC_EVERY_ALLOC and make it pass.
  for (int i = 0; i < 100; ++i) {
    hnode_t* t1 = b->AbbreviatedTree();
    ASSERT(strcmp("hnode.Record", hnode_str(t1->tag_())) == 0);

    auto f = mylib::Stdout();
    auto ast_f = new format::TextOutput(f);
    format::PrintTree(t1, ast_f);
    log("");
  }

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gc_heap::gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(pretty_print_test);

  GREATEST_MAIN_END();
  return 0;
}
