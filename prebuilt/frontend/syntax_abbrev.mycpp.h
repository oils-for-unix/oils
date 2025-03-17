// prebuilt/frontend/syntax_abbrev.mycpp.h: GENERATED by mycpp

#ifndef FRONTEND_SYNTAX_ABBREV_H
#define FRONTEND_SYNTAX_ABBREV_H

#include "_gen/asdl/hnode.asdl.h"
#include "_gen/display/pretty.asdl.h"
#include "cpp/data_lang.h"
#include "mycpp/runtime.h"

namespace syntax_asdl {
  class Token;
  class CompoundWord;
  class DoubleQuoted;
  class SingleQuoted;
  class SimpleVarSub;
  class BracedVarSub;

  class command__Simple;
  class expr__Const;
  class expr__Var;
}

namespace syntax_abbrev {  // forward declare
}

namespace syntax_abbrev {  // declare

void _AbbreviateToken(syntax_asdl::Token* tok, List<hnode_asdl::hnode_t*>* out);
hnode_asdl::hnode_t* _Token(syntax_asdl::Token* obj);
hnode_asdl::hnode_t* _CompoundWord(syntax_asdl::CompoundWord* obj);
hnode_asdl::hnode_t* _DoubleQuoted(syntax_asdl::DoubleQuoted* obj);
hnode_asdl::hnode_t* _SingleQuoted(syntax_asdl::SingleQuoted* obj);
hnode_asdl::hnode_t* _SimpleVarSub(syntax_asdl::SimpleVarSub* obj);
hnode_asdl::hnode_t* _BracedVarSub(syntax_asdl::BracedVarSub* obj);
hnode_asdl::hnode_t* _command__Simple(syntax_asdl::command__Simple* obj);
hnode_asdl::hnode_t* _expr__Var(syntax_asdl::expr__Var* obj);
hnode_asdl::hnode_t* _expr__Const(syntax_asdl::expr__Const* obj);

}  // declare namespace syntax_abbrev

#endif  // FRONTEND_SYNTAX_ABBREV_H
