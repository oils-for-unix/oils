// pgen2_parse.h

#ifndef PGEN2_PARSE_H
#define PGEN2_PARSE_H

#include "id_kind_asdl.h"
#include "mylib.h"
#include "syntax_asdl.h"

// Hacky forward declaration for translated pgen2/pnode.py
// Note: it's probably better to express PNode in ASDL, like Token.
namespace pnode {
class PNode;
}
// Hacky stub
namespace grammar {
class Grammar;
}

namespace parse {

class ParseError {
 public:
  ParseError(Str* msg, int type_, syntax_asdl::Token* tok);

  Str* msg;
  syntax_asdl::Token* tok;
  int type;
};

class Parser {
 public:
  // In C, the grammar is a constant, so the grammar arg is ignored.  (We can't
  // get easily rid of it because the call site has to type check and run in
  // Python.)
  Parser(grammar::Grammar* grammar) {
  }
  void setup(int start);
  bool addtoken(int typ, syntax_asdl::Token* opaque, int ilabel);

  // Probably should delete these
  // void shift(int typ, syntax_asdl::Token* opaque, int newstate);
  // void push(int typ, syntax_asdl::Token* opaque, Tuple2<List<List<Tuple2<int,
  // int>*>*>*, Dict<int, int>*>* newdfa, int newstate);  void pop();

  // grammar::Grammar* grammar;
  pnode::PNode* rootnode;
  // List<parse::_StackItem*>* stack;
};

}  // namespace parse

#endif  // PGEN2_PARSE_H
