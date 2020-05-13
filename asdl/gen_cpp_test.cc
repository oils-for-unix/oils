#include <stdarg.h>  // va_list, etc.
#include <stdio.h>

#include "greatest.h"
#include "mylib.h"
#include "typed_arith_asdl.h"
#include "typed_demo_asdl.h"  // has simple Sum, etc

using typed_arith_asdl::pipeline;

namespace arith_expr_e = typed_arith_asdl::arith_expr_e;
using typed_arith_asdl::arith_expr_t;

using typed_arith_asdl::arith_expr__Const;
using typed_arith_asdl::arith_expr__FuncCall;
using typed_arith_asdl::arith_expr__Unary;
using typed_arith_asdl::arith_expr__Var;

using typed_demo_asdl::bool_expr__LogicalBinary;
using typed_demo_asdl::op_id_e;

using hnode_asdl::hnode__Leaf;
using hnode_asdl::hnode_str;
namespace hnode_e = hnode_asdl::hnode_e;

// Log messages to stdout.
void log(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  va_end(args);
  fprintf(stderr, "\n");
}

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

TEST misc_test() {
  auto c = new arith_expr__Const(42);
  log("sizeof *c = %d", sizeof *c);  // hm only 8

  ASSERT_EQ_FMT(42, c->i, "%d");
  log("c->tag = %d", c->tag_());
  PrintTag(c);

  auto v = new arith_expr__Var(new Str("foo"));
  log("sizeof *v = %d", sizeof *v);  // 16

  ASSERT(str_equals(new Str("foo"), v->name));
  log("v->tag = %d", v->tag_());
  PrintTag(v);

  auto u = new arith_expr__Unary(new Str("-"), v);
  log("u->op = %s", u->op->data_);

  auto v1 = new arith_expr__Var(new Str("v1"));
  auto v2 = new arith_expr__Var(new Str("v2"));
  auto args = new List<arith_expr_t*>{v1, v2};

  auto f = new arith_expr__FuncCall(new Str("f"), args);
  log("f->name = %s", f->name->data_);

  auto p = new pipeline(true);
  log("p->negated = %d", p->negated);

  // from typed_demo.asdl

  auto o = op_id_e::Plus;
  auto b = new bool_expr__LogicalBinary(o, nullptr, nullptr);
  log("sizeof b = %d", sizeof b);
  log("");

  hnode_t* t = c->AbbreviatedTree();
  ASSERT(strcmp("hnode.Record", hnode_str(t->tag_())) == 0);

  typed_demo_asdl::maps m;
  log("m.ss  = %p", m.ss);
  log("m.ib = %p", m.ib);

  m.ss = new Dict<Str*, Str*>();
  m.ib = new Dict<int, bool>();

  m.ss->set(new Str("foo"), new Str("bar"));

  m.ib->set(42, true);
  log("mm.ib[42] = %d", m.ib->get(3));

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

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  GREATEST_MAIN_BEGIN();
  RUN_TEST(misc_test);
  GREATEST_MAIN_END(); /* display results */
  return 0;
}
