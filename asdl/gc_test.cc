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

using typed_demo_asdl::a_word;
using typed_demo_asdl::a_word_e;
using typed_demo_asdl::a_word_t;
using typed_demo_asdl::arith_expr;
using typed_demo_asdl::arith_expr_e;
using typed_demo_asdl::bool_expr__Binary;
using typed_demo_asdl::CompoundWord;
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
    hnode_t* t1 = b->PrettyTree(false);
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
  ASSERT_EQ_FMT(7, gHeap.Collect(), "%d");

  h = rec;  // base type
  array->children->append(h);

  format::PrintTree(h, ast_f);
  printf("\n");
  ASSERT_EQ_FMT(8, gHeap.Collect(), "%d");

  h = Alloc<hnode__Leaf>(StrFromC("zz"), color_e::TypeName);
  array->children->append(h);

  format::PrintTree(h, ast_f);
  printf("\n");
  ASSERT_EQ_FMT(10, gHeap.Collect(), "%d");

  h = array;
  format::PrintTree(h, ast_f);
  printf("\n");
  ASSERT_EQ_FMT(10, gHeap.Collect(), "%d");

  PASS();
}

TEST subtype_test() {
  List<CompoundWord*>* li = nullptr;
  StackRoot _r(&li);

  // Test the GC header

  li = NewList<CompoundWord*>();

  int n = 1000;
  for (int i = 0; i < n; ++i) {
    auto* c = Alloc<CompoundWord>();

    c->append(arith_expr::NoOp);
    c->append(Alloc<arith_expr::Const>(42));

    // log("len(c) %d", len(c));
    // log("i = %d", i);

    ASSERT_EQ_FMT(i, len(li), "%d");
    li->append(c);
    mylib::MaybeCollect();
  }

  log("len(li) = %d", len(li));
  ASSERT_EQ(n, len(li));

  // Now test the type tag

  List<a_word_t*>* words = nullptr;
  StackRoot _r2(&words);

  words = NewList<a_word_t*>();

#if 1
  n = 100;
  for (int i = 0; i < n; ++i) {
    words->append(Alloc<CompoundWord>());
    words->append(Alloc<a_word::String>(kEmptyString));

    // mylib::MaybeCollect();
  }
#endif

  log("len(words) = %d", len(words));
  ASSERT_EQ(n * 2, len(words));

  int num_c = 0;
  int num_s = 0;
  for (int i = 0; i < len(words); ++i) {
    auto* w = words->at(i);
    switch (w->tag()) {
    case a_word_e::CompoundWord: {
      // printf("CompoundWord\n");
      num_c++;
      break;
    }
    case a_word_e::String: {
      // printf("String\n");
      num_s++;
      break;
    }
    default: {
      FAIL();
    }
    }
  }
  log("CompoundWord %d, String %d", num_c, num_s);

  PASS();
}

TEST print_subtype_test() {
  // TODO: Also need to test GC header for List[int] subtypes

  auto c = Alloc<CompoundWord>();

  log("len = %d", len(c));

  c->append(arith_expr::NoOp);
  c->append(Alloc<arith_expr::Const>(42));

  log("len = %d", len(c));

#if 1
  hnode_t* t1 = c->PrettyTree(false);
  // ASSERT_EQ_FMT(hnode_e::Record, t1->tag(), "%d");

  auto f = mylib::Stdout();
  auto ast_f = Alloc<format::TextOutput>(f);
  format::PrintTree(t1, ast_f);
  printf("\n");
#endif

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(hnode_test);
  gHeap.Collect();

  RUN_TEST(pretty_print_test);

  RUN_TEST(subtype_test);
  RUN_TEST(print_subtype_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();
  return 0;
}
