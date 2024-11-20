// asdl/gc_test.cc

#include "_gen/asdl/examples/typed_demo.asdl.h"
#include "_gen/asdl/hnode.asdl.h"
#include "mycpp/runtime.h"
#include "prebuilt/asdl/runtime.mycpp.h"
#include "vendor/greatest.h"

using hnode_asdl::color_e;
using hnode_asdl::hnode;
using hnode_asdl::hnode__Array;
using hnode_asdl::hnode__Leaf;
using hnode_asdl::hnode__Record;
using hnode_asdl::hnode_e;
using hnode_asdl::hnode_t;

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

  for (int i = 0; i < 2000; ++i) {
    hnode_t* t1 = b->PrettyTree();
    ASSERT_EQ(hnode_e::Record, t1->tag());

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

TEST hnode_test() {
  mylib::Writer* f = nullptr;
  format::TextOutput* ast_f = nullptr;
  hnode_t* h = nullptr;           // base type
  hnode__Array* array = nullptr;  // base type
  hnode__Record* rec = nullptr;
  StackRoots _roots({&f, &ast_f, &h, &array, &rec});

  f = mylib::Stdout();
  ast_f = Alloc<format::TextOutput>(f);
  array = hnode::Array::CreateNull(true);
  ASSERT_EQ_FMT(4, gHeap.Collect(), "%d");

  rec = hnode::Record::CreateNull(true);
  rec->node_type = StrFromC("dummy_node");
  ASSERT_EQ_FMT(8, gHeap.Collect(), "%d");

  h = rec;  // base type
  array->children->append(h);

  format::PrintTree(h, ast_f);
  printf("\n");
  ASSERT_EQ_FMT(9, gHeap.Collect(), "%d");

  h = Alloc<hnode__Leaf>(StrFromC("zz"), color_e::TypeName);
  array->children->append(h);

  format::PrintTree(h, ast_f);
  printf("\n");
  ASSERT_EQ_FMT(11, gHeap.Collect(), "%d");

  h = array;
  format::PrintTree(h, ast_f);
  printf("\n");
  ASSERT_EQ_FMT(11, gHeap.Collect(), "%d");

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(hnode_test);
  gHeap.Collect();

  RUN_TEST(pretty_print_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
