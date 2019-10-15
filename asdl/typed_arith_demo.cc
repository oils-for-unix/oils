#include <stdarg.h>  // va_list, etc.
#include <stdio.h>

#include "typed_arith.asdl.h"
#include "typed_demo.asdl.h"  // has simple Sum, etc
#include "mylib.h"

using typed_arith_asdl::pipeline;

using typed_arith_asdl::arith_expr_e;
using typed_arith_asdl::arith_expr_t;

using typed_arith_asdl::arith_expr__Const;
using typed_arith_asdl::arith_expr__Var;
using typed_arith_asdl::arith_expr__Unary;
using typed_arith_asdl::arith_expr__FuncCall;

using typed_demo_asdl::bool_expr__LogicalBinary;
using typed_demo_asdl::op_id_e;


// Log messages to stdout.
void log(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  va_end(args);
  fprintf(stderr, "\n");
}

void PrintTag(arith_expr_t* a) {
  switch (a->tag) {
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

int main(int argc, char **argv) {
  auto c = new arith_expr__Const(42);
  log("sizeof *c = %d", sizeof *c);  // hm only 8
  log("c->i = %d", c->i);
  log("c->tag = %d", c->tag);
  PrintTag(c);

  auto v = new arith_expr__Var(new Str("foo"));
  log("sizeof *v = %d", sizeof *v);  // 16
  log("v->name = %s", v->name->data_);
  log("v->tag = %d", v->tag);
  PrintTag(v);

  auto u = new arith_expr__Unary(new Str("-"), v);
  log("u->op = %s", u->op->data_);

  auto v1 = new arith_expr__Var(new Str("v1"));
  auto v2 = new arith_expr__Var(new Str("v2"));
  auto args = new List<arith_expr_t*> {v1, v2};

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
  log("%s", hnode_str(t->tag));
  log("");

  using hnode_asdl::hnode_e;
  if (t->tag == hnode_e::Leaf) {
    hnode__Leaf* t2 = static_cast<hnode__Leaf*>(t);
    log("%s", hnode_str(t2->tag));
    log("%s", color_str(t2->color));
    log("%s", t2->s->data_);
  }
  // NOTE: This is self-initialization!!!
  /*
  if (t->tag == hnode_e::Leaf) {
    hnode__Leaf* t = static_cast<hnode__Leaf*>(t);
    log("%s", hnode_str(t->tag));
    log("%s", color_str(t->color));
    log("%s", t->s->data_);
  }
  */
}

