// pgen2.h

#ifndef CPP_PGEN2_H
#define CPP_PGEN2_H

#include "_gen/frontend/id_kind.asdl.h"
#include "_gen/frontend/syntax.asdl.h"
#include "mycpp/runtime.h"

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
  ParseError(Str* msg, int type_, syntax_asdl::Token* tok) {
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(ParseError));
  }

  static constexpr uint32_t field_mask() {
    return maskbit(offsetof(ParseError, msg)) |
           maskbit(offsetof(ParseError, tok));
  }

  Str* msg;
  syntax_asdl::Token* tok;
  int type;
};

class Parser {
 public:
  // In C, the grammar is a constant, so the grammar arg is ignored.  (We can't
  // get easily rid of it because the call site has to type check and run in
  // Python.)
  explicit Parser(grammar::Grammar* grammar) {
  }
  void setup(int start);
  bool addtoken(int typ, syntax_asdl::Token* opaque, int ilabel);

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(Parser));
  }

  static constexpr uint32_t field_mask() {
    return maskbit(offsetof(Parser, rootnode));
  }

  // Probably should delete these
  // void shift(int typ, syntax_asdl::Token* opaque, int newstate);
  // void push(int typ, syntax_asdl::Token* opaque, Tuple2<List<List<Tuple2<int,
  // int>*>*>*, Dict<int, int>*>* newdfa, int newstate);  void pop();

  // grammar::Grammar* grammar;
  pnode::PNode* rootnode;
  // List<parse::_StackItem*>* stack;
};

}  // namespace parse

#endif  // CPP_PGEN2_H
