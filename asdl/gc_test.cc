// asdl/gc_test.cc

#include "_gen/asdl/examples/typed_demo.asdl.h"
#include "_gen/asdl/hnode.asdl.h"
#include "mycpp/runtime.h"
#include "prebuilt/asdl/runtime.mycpp.h"
#include "vendor/greatest.h"

using hnode_asdl::color_e;
using hnode_asdl::hnode_t;
using hnode_asdl::hnode__Array;
using hnode_asdl::hnode__Record;
using hnode_asdl::hnode__Leaf;
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
  for (int i = 0; i < 2; ++i) {
    hnode_t* t1 = b->PrettyTree();
    ASSERT_EQ(hnode_e::Record, t1->tag_());

    auto f = mylib::Stdout();
    auto ast_f = Alloc<format::TextOutput>(f);
    format::PrintTree(t1, ast_f);
    log("");
  }

  PASS();
}

// TODO:
// - This test is complex and not very good
// - Maybe unify this with gen_cpp_test.cc
// - Port build to Ninja
// - Make it ASAN-clean

TEST hnode_test() {
  mylib::Writer* f = nullptr;
  format::TextOutput* ast_f = nullptr;
  hnode__Array* array = nullptr;  // base type
  hnode_t* h = nullptr;  // base type
  StackRoots _roots({&f, &ast_f, &h, &array});

  f = mylib::Stdout();
  ast_f = Alloc<format::TextOutput>(f);
  array = Alloc<hnode__Array>();

  hnode__Record* rec = Alloc<hnode__Record>();
  rec->node_type = StrFromC("dummy_node");

  h = rec;  // base type
  array->children->append(h);

  format::PrintTree(h, ast_f);
  printf("\n");
  gHeap.Collect();

  h = Alloc<hnode__Leaf>(StrFromC("zz"), color_e::TypeName);
  array->children->append(h);

  format::PrintTree(h, ast_f);
  printf("\n");
  gHeap.Collect();

  h = array;
  format::PrintTree(h, ast_f);
  printf("\n");
  gHeap.Collect();

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init(KiB(128));

  GREATEST_MAIN_BEGIN();

  RUN_TEST(hnode_test);
  RUN_TEST(pretty_print_test);

  gHeap.Collect();

  GREATEST_MAIN_END();
  return 0;
}
