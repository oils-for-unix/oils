#include <stdarg.h>  // va_list, etc.
#include <stdio.h>

#include "typed_arith.asdl.h"
#include "typed_demo.asdl.h"  // has simple Sum, etc
#include "runtime.h"

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
  auto c = new arith_expr::Const(42);
  log("c->i = %d", c->i);
  log("c->tag = %d", c->tag);
  PrintTag(c);

  auto v = new arith_expr::Var(new Str("foo"));
  log("v->name = %s", v->name->data_);
  log("v->tag = %d", v->tag);
  PrintTag(v);

  auto u = new arith_expr::Unary(new Str("-"), v);
  log("u->op = %s", u->op->data_);

  auto v1 = new arith_expr::Var(new Str("v1"));
  auto v2 = new arith_expr::Var(new Str("v2"));
  auto args = new List<arith_expr_t*> {v1, v2};

  auto f = new arith_expr::FuncCall(new Str("f"), args);
  log("f->name = %s", f->name->data_);

  auto p = new pipeline(true);
  log("p->negated = %d", p->negated);

  // from typed_demo.asdl

  auto o = op_id_e::Plus;
  auto b = new bool_expr::LogicalBinary(o, nullptr, nullptr);
  log("sizeof b = %d", sizeof b);

  //log("u->a->name = %s", u->a->name->data_);
}

