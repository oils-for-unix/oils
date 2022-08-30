// asdl/gc_test.cc

#include "_gen/asdl/typed_demo_asdl.h"
#include "_build/cpp/hnode_asdl.h"
#include "mycpp/gc_containers.h"
#include "mycpp/gc_mylib.h"
#include "prebuilt/asdl/runtime.mycpp.h"
#include "vendor/greatest.h"

using hnode_asdl::hnode_t;
namespace hnode_e = hnode_asdl::hnode_e;

using typed_demo_asdl::bool_expr__Binary;
using typed_demo_asdl::word;

TEST pretty_print_test() {
  auto w1 = Alloc<word>(StrFromC("left"));
  auto w2 = Alloc<word>(StrFromC("right"));
  auto b = Alloc<bool_expr__Binary>(w1, w2);

#if 0
  log("sizeof b = %d", sizeof b);
  log("");
#endif

  // Note: this segfaults with 1000 iterations, because it hit GC.
  // TODO: GC_EVERY_ALLOC and make it pass.
  for (int i = 0; i < 100; ++i) {
    hnode_t* t1 = b->PrettyTree();
    ASSERT_EQ(hnode_e::Record, t1->tag_());

    auto f = mylib::Stdout();
    auto ast_f = new format::TextOutput(f);
    format::PrintTree(t1, ast_f);
    log("");
  }

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(pretty_print_test);

  GREATEST_MAIN_END();
  return 0;
}
