// Replacement for osh/arith_spec

#ifndef ARITH_SPEC_H
#define ARITH_SPEC_H

#include "id_kind_asdl.h"
#include "syntax_asdl.h"

using syntax_asdl::arith_expr_t;
using syntax_asdl::word_t;

namespace tdop {
  class TdopParser;  // forward declaration

  typedef arith_expr_t* (*LeftFunc)(TdopParser*, word_t*, arith_expr_t*, int);
  typedef arith_expr_t* (*NullFunc)(TdopParser* , word_t*, int);

  class LeftInfo {
   public:
    LeftFunc led;
    int lbp;
    int rbp;
  };

  class NullInfo {
   public:
    NullFunc nud;
    int bp;
  };

  class ParserSpec {
   public:
    LeftInfo* LookupLed(Id_t id);  // int is Id_t
    NullInfo* LookupNud(Id_t id);
  };
}

namespace arith_spec {

tdop::ParserSpec* Spec();

}  // arith_spec

#endif  // ARITH_SPEC_H
