#include <stdarg.h>  // va_list, etc.
#include <stdio.h>

#include "_gen/asdl/typed_arith_asdl.h"
#include "_gen/asdl/typed_demo_asdl.h"  // has simple Sum, etc
#include "mycpp/oldstl_containers.h"
#include "prebuilt/asdl/runtime.mycpp.h"
#include "vendor/greatest.h"

using typed_arith_asdl::pipeline;

namespace arith_expr_e = typed_arith_asdl::arith_expr_e;
using typed_arith_asdl::arith_expr_t;

using typed_arith_asdl::arith_expr__Const;
using typed_arith_asdl::arith_expr__FuncCall;
using typed_arith_asdl::arith_expr__Unary;
using typed_arith_asdl::arith_expr__Var;

using typed_demo_asdl::bool_expr__Binary;
using typed_demo_asdl::bool_expr__LogicalBinary;
using typed_demo_asdl::op_id_e;

using hnode_asdl::hnode__Leaf;
namespace hnode_e = hnode_asdl::hnode_e;

void PrintTag(arith_expr_t* a) {
  switch (a->tag_()) {
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

#if 1
TEST misc_test() {
  auto c = new arith_expr__Const(42);
  log("sizeof *c = %d", sizeof *c);  // 16 bytes

  ASSERT_EQ_FMT(42, c->i, "%d");
  log("c->tag = %d", c->tag_());
  PrintTag(c);

  auto v = new arith_expr__Var(StrFromC("foo"));
  log("sizeof *v = %d", sizeof *v);  // 24 bytes

  ASSERT(str_equals(StrFromC("foo"), v->name));
  log("v->tag = %d", v->tag_());
  PrintTag(v);

  auto u = new arith_expr__Unary(StrFromC("-"), v);
  log("u->op = %s", u->op->data_);

  auto v1 = new arith_expr__Var(StrFromC("v1"));
  auto v2 = new arith_expr__Var(StrFromC("v2"));
  auto args = NewList<arith_expr_t*>({v1, v2});

  auto f = new arith_expr__FuncCall(StrFromC("f"), args);
  log("f->name = %s", f->name->data_);

  auto p = new pipeline(true);
  log("p->negated = %d", p->negated);

#if 0
  if (t->tag_() == hnode_e::Leaf) {
    hnode__Leaf* t2 = static_cast<hnode__Leaf*>(t);
    log("%s", hnode_str(t2->tag_()));
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
#endif

TEST pretty_print_test() {
  // typed_demo.asdl

  // auto o = op_id_e::Plus;
  // Note: this is NOT prevented at compile time, even though it's illegal.
  // left and right are not optional.
  // auto b = new bool_expr__LogicalBinary(o, nullptr, nullptr);

  auto w1 = new typed_demo_asdl::word(StrFromC("left"));
  auto w2 = new typed_demo_asdl::word(StrFromC("right"));
  auto b = new bool_expr__Binary(w1, w2);
  //
  log("sizeof b = %d", sizeof b);
  log("");
  hnode_t* t1 = b->PrettyTree();
  ASSERT_EQ(hnode_e::Record, t1->tag_());

  auto f = mylib::Stdout();
  auto ast_f = new format::TextOutput(f);
  format::PrintTree(t1, ast_f);

  // typed_arith.asdl
  auto c = new arith_expr__Const(42);
  hnode_t* t2 = c->PrettyTree();
  ASSERT_EQ(hnode_e::Record, t2->tag_());

  PASS();
}

TEST maps_test() {
  typed_demo_asdl::maps m;
  log("m.ss  = %p", m.ss);
  log("m.ib = %p", m.ib);

  m.ss = new Dict<Str*, Str*>();
  m.ib = new Dict<int, bool>();

  m.ss->set(StrFromC("foo"), StrFromC("bar"));

  m.ib->set(42, true);
  // note: Dict<int, bool>::get() doesn't compile because nullptr isn't valid
  // to return.  But Dict<int, bool>::index() does compile.
  log("mm.ib[42] = %d", m.ib->index_(42));

  hnode_t* t = m.PrettyTree();
  auto f = mylib::Stdout();
  auto ast_f = new format::TextOutput(f);
  // fails with repr(void *)
  // OK change the pretty printer!
  format::PrintTree(t, ast_f);

  PASS();
}

using typed_demo_asdl::SetToArg_;
namespace flag_type = typed_demo_asdl::flag_type;

// TODO: We should always use these, rather than 'new flag_type::Bool()'
flag_type::Bool g_ft = {};

// Use __ style
using typed_demo_asdl::cflow__Return;
cflow__Return g_ret = {5};

int i0 = 7;  // This runs before main()?  How to tell?
List<int> *g_list = NewList<int>({i0, 8, 9});

// Dict<Str*, int> g_dict = {4, 5, 6};

TEST literal_test() {
  // Interesting, initializer list part of the constructor "runs".  Otherwise
  // this doesn't work.
  log("g_ft.tag_() = %d", g_ft.tag_());
  auto ft = new flag_type::Bool();
  ASSERT_EQ(g_ft.tag_(), ft->tag_());

  log("g_ret.tag_() = %d", g_ret.tag_());
  log("g_ret.status = %d", g_ret.status);
  auto ret = new cflow__Return(5);
  ASSERT_EQ(g_ret.tag_(), ret->tag_());
  ASSERT_EQ(g_ret.status, ret->status);

  // Wow this works too?  Is it the the constexpr interpreter, or is this code
  // inserted before main()?
  ASSERT_EQ(3, len(g_list));
  ASSERT_EQ_FMT(7, g_list->index_(0), "%d");
  ASSERT_EQ_FMT(8, g_list->index_(1), "%d");
  ASSERT_EQ_FMT(9, g_list->index_(2), "%d");

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(misc_test);
  RUN_TEST(pretty_print_test);
  RUN_TEST(maps_test);
  RUN_TEST(literal_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
