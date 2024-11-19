#include <stdarg.h>  // va_list, etc.
#include <stdio.h>

#include "_gen/asdl/examples/shared_variant.asdl.h"
#include "_gen/asdl/examples/typed_arith.asdl.h"
#include "_gen/asdl/examples/typed_demo.asdl.h"  // has simple Sum, etc
#include "mycpp/runtime.h"
#include "prebuilt/asdl/runtime.mycpp.h"
#include "vendor/greatest.h"

using typed_arith_asdl::pipeline;

using typed_arith_asdl::arith_expr;    // variant type namespace
using typed_arith_asdl::arith_expr_e;  // variant tag type
using typed_arith_asdl::arith_expr_t;  // sum type

using typed_arith_asdl::arith_expr__Big;
using typed_arith_asdl::arith_expr__Const;
using typed_arith_asdl::arith_expr__FuncCall;
using typed_arith_asdl::arith_expr__Unary;
using typed_arith_asdl::arith_expr__Var;
using typed_arith_asdl::CompoundWord;

using typed_demo_asdl::bool_expr__Binary;
using typed_demo_asdl::bool_expr__LogicalBinary;
using typed_demo_asdl::op_array;
using typed_demo_asdl::op_id_e;

using hnode_asdl::hnode__Leaf;
using hnode_asdl::hnode_e;

void PrintTag(arith_expr_t* a) {
  switch (a->tag()) {
  case arith_expr_e::Const:
    log("Const");
    break;
  case arith_expr_e::Var:
    log("Var");
    break;
  default:
    log("OTHER");
  }
  log("");
}

TEST misc_test() {
  auto c = Alloc<arith_expr::Const>(42);
  log("sizeof *c = %d", sizeof *c);  // 16 bytes

  ASSERT_EQ_FMT(42, c->i, "%d");
  log("c->tag = %d", c->tag());
  PrintTag(c);

  auto v = Alloc<arith_expr__Var>(StrFromC("foo"));
  log("sizeof *v = %d", sizeof *v);  // 24 bytes

  ASSERT(str_equals(StrFromC("foo"), v->name));
  log("v->tag = %d", v->tag());
  PrintTag(v);

  auto u = Alloc<arith_expr__Unary>(StrFromC("-"), v);
  log("u->op = %s", u->op->data_);

  auto v1 = Alloc<arith_expr__Var>(StrFromC("v1"));
  auto v2 = Alloc<arith_expr__Var>(StrFromC("v2"));
  auto args = NewList<arith_expr_t*>({v1, v2});

  auto f = Alloc<arith_expr__FuncCall>(StrFromC("f"), args);
  log("f->name = %s", f->name->data_);

  auto p = Alloc<pipeline>(true);
  log("p->negated = %d", p->negated);

#if 0
  if (t->tag() == hnode_e::Leaf) {
    hnode__Leaf* t2 = static_cast<hnode__Leaf*>(t);
    log("%s", hnode_str(t2->tag()));
    log("%s", color_str(t2->color));
    log("%s", t2->s->data_);
  }
#endif

  // NOTE: This is self-initialization!!!
  /*
  if (t->tag == hnode_e::Leaf) {
    hnode__Leaf* t = static_cast<hnode__Leaf*>(t);
    log("%s", hnode_str(t->tag));
    log("%s", color_str(t->color));
    log("%s", t->s->data_);
  }
  */

  PASS();
}

using shared_variant_asdl::DoubleQuoted;
using shared_variant_asdl::word_part_e;
using shared_variant_asdl::word_part_t;

using shared_variant_asdl::tok;
using shared_variant_asdl::tok_e;
using shared_variant_asdl::tok_t;
using shared_variant_asdl::Token;

TEST shared_variant_test() {
  auto* dq = Alloc<DoubleQuoted>(0, Alloc<List<BigStr*>>());

  word_part_t* wp = nullptr;
  wp = dq;  // assign to base type

  log("wp->tag() %d", wp->tag());

  auto* token = Alloc<Token>(0, StrFromC("hi"));
  tok_t* tok = nullptr;
  tok = token;

  log("tok->tag() for Token = %d", tok->tag());

  auto* eof = tok::Eof;
  tok = eof;
  log("tok->tag() for Eof = %d", tok->tag());

  PASS();
}

using typed_demo_asdl::bool_expr_str;

TEST pretty_print_test() {
  // typed_demo.asdl

  // auto o = op_id_e::Plus;
  // Note: this is NOT prevented at compile time, even though it's illegal.
  // left and right are not optional.
  // auto b = new bool_expr__LogicalBinary(o, nullptr, nullptr);

  auto w1 = Alloc<typed_demo_asdl::word>(StrFromC("left"));
  auto w2 = Alloc<typed_demo_asdl::word>(StrFromC("right"));
  auto b = Alloc<bool_expr__Binary>(w1, w2);

  hnode_t* t1 = b->PrettyTree();
  ASSERT_EQ_FMT(hnode_e::Record, t1->tag(), "%d");

  auto f = mylib::Stdout();
  auto ast_f = Alloc<format::TextOutput>(f);
  format::PrintTree(t1, ast_f);
  printf("\n");

  log("bool_expr_str = %s", bool_expr_str(b->tag())->data_);
  ASSERT(str_equals0("bool_expr.Binary", bool_expr_str(b->tag())));

  ASSERT(str_equals0("Binary", bool_expr_str(b->tag(), false)));

  // typed_arith.asdl
  auto* c = Alloc<arith_expr__Const>(42);
  hnode_t* t2 = c->PrettyTree();
  ASSERT_EQ(hnode_e::Record, t2->tag());
  format::PrintTree(t2, ast_f);
  printf("\n");

  auto* big = Alloc<arith_expr__Big>(mops::BigInt(INT64_MAX));
  hnode_t* t3 = big->PrettyTree();
  ASSERT_EQ(hnode_e::Record, t3->tag());
  format::PrintTree(t3, ast_f);
  printf("\n");

  auto* args =
      NewList<arith_expr_t*>(std::initializer_list<arith_expr_t*>{c, big});
  auto* func = Alloc<arith_expr::FuncCall>(StrFromC("myfunc"), args);
  hnode_t* t4 = func->PrettyTree();
  ASSERT_EQ(hnode_e::Record, t4->tag());
  format::PrintTree(t4, ast_f);

  PASS();
}

TEST dicts_test() {
  auto m = typed_demo_asdl::Dicts::CreateNull();
  log("m.ss = %p", m->ss);
  log("m.ib = %p", m->ib);

  m->ss = Alloc<Dict<BigStr*, BigStr*>>();
  m->ib = Alloc<Dict<int, bool>>();

  m->ss->set(StrFromC("foo"), StrFromC("bar"));

  m->ib->set(42, true);
  // note: Dict<int, bool>::get() doesn't compile because nullptr isn't valid
  // to return.  But Dict<int, bool>::index() does compile.
  log("mm.ib[42] = %d", m->ib->at(42));

  hnode_t* t = m->PrettyTree();
  auto f = mylib::Stdout();
  auto ast_f = Alloc<format::TextOutput>(f);
  // fails with repr(void *)
  // OK change the pretty printer!
  format::PrintTree(t, ast_f);

  PASS();
}

using typed_demo_asdl::flag_type;
using typed_demo_asdl::flag_type__Bool;
using typed_demo_asdl::SetToArg_;

ObjHeader make_global(ObjHeader header) {
  header.heap_tag = HeapTag::Global;
  return header;
}

// TODO: We should always use these, rather than 'new flag_type::Bool()'
GcGlobal<flag_type__Bool> g_ft = {make_global(flag_type__Bool::obj_header())};

// Use __ style
using typed_demo_asdl::cflow__Return;
GcGlobal<cflow__Return> g_ret = {make_global(cflow__Return::obj_header()), {5}};

int i0 = 7;

// NOTE: This causes an failed assert() in the GC runtime
#if 0
List<int>* g_list = NewList<int>({i0, 8, 9});
#endif

// Dict<BigStr*, int> g_dict = {4, 5, 6};

TEST literal_test() {
  // Interesting, initializer list part of the constructor "runs".  Otherwise
  // this doesn't work.
  log("g_ft.tag() = %d", g_ft.obj.tag());
  auto ft = flag_type::Bool;
  ASSERT_EQ(g_ft.obj.tag(), ft->tag());

  log("g_ret.tag() = %d", g_ret.obj.tag());
  log("g_ret.status = %d", g_ret.obj.status);
  auto ret = Alloc<cflow__Return>(5);
  ASSERT_EQ(g_ret.obj.tag(), ret->tag());
  ASSERT_EQ(g_ret.obj.status, ret->status);

#if 0
  // Wow this works too?  Is it the the constexpr interpreter, or is this code
  // inserted before main()?
  ASSERT_EQ(3, len(g_list));
  ASSERT_EQ_FMT(7, g_list->at(0), "%d");
  ASSERT_EQ_FMT(8, g_list->at(1), "%d");
  ASSERT_EQ_FMT(9, g_list->at(2), "%d");
#endif

  PASS();
}

TEST string_defaults_test() {
  auto st = Alloc<typed_demo_asdl::Strings>(kEmptyString, kEmptyString);
  ASSERT_EQ(kEmptyString, st->required);
  ASSERT_EQ(kEmptyString, st->optional);

  st = typed_demo_asdl::Strings::CreateNull();
  ASSERT_EQ(kEmptyString, st->required);
  ASSERT_EQ(nullptr, st->optional);

  st = Alloc<typed_demo_asdl::Strings>(kEmptyString, nullptr);
  ASSERT_EQ(kEmptyString, st->required);
  ASSERT_EQ(nullptr, st->optional);

  PASS();
}

TEST list_defaults_test() {
  auto o = op_array::CreateNull();
  ASSERT_EQ(nullptr, o->ops);

  // Empty list
  auto o2 = op_array::CreateNull(true);
  ASSERT_EQ(0, len(o2->ops));

  PASS();
}

TEST subtype_test() {
  // TODO: Also need to test GC header for List[int] subtypes

  auto c = Alloc<CompoundWord>();

  log("len = %d", len(c));

  c->append(arith_expr::NoOp);
  c->append(Alloc<arith_expr::Const>(42));

  log("len = %d", len(c));

#if 1
  hnode_t* t1 = c->PrettyTree();
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

  RUN_TEST(misc_test);
  RUN_TEST(shared_variant_test);
  RUN_TEST(pretty_print_test);
  RUN_TEST(dicts_test);
  RUN_TEST(literal_test);
  RUN_TEST(string_defaults_test);
  RUN_TEST(list_defaults_test);
  RUN_TEST(subtype_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();

  return 0;
}
