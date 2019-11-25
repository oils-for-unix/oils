// Replacement for osh/arith_spec
// TODO: This should be frontend_tdop.h,cc

#ifndef ARITH_SPEC_H
#define ARITH_SPEC_H

#include "id_kind_asdl.h"
using id_kind_asdl::Id_t;
#include "syntax_asdl.h"

using syntax_asdl::arith_expr_t;
using syntax_asdl::word_t;

// move to tdop.h?
namespace tdop {
  class TdopParser;  // forward declaration

  // Duplicated function prototypes
  arith_expr_t* NullError(TdopParser* p, word_t* t, int bp);
  arith_expr_t* NullConstant(TdopParser* p, word_t* w, int bp);
  arith_expr_t* NullParen(TdopParser* p, word_t* t, int bp);
  arith_expr_t* NullPrefixOp(TdopParser* p, word_t* w, int bp);
  arith_expr_t* LeftError(TdopParser* p, word_t* t, arith_expr_t* left, int rbp);
  arith_expr_t* LeftBinaryOp(TdopParser* p, word_t* w, arith_expr_t* left, int rbp);
  arith_expr_t* LeftAssign(TdopParser* p, word_t* w, arith_expr_t* left, int rbp);

  typedef arith_expr_t* (*LeftFunc)(TdopParser*, word_t*, arith_expr_t*, int);
  typedef arith_expr_t* (*NullFunc)(TdopParser*, word_t*, int);

  struct LeftInfo {
    LeftFunc led;
    int lbp;
    int rbp;
  };

  struct NullInfo {
    NullFunc nud;
    int bp;
  };

  class ParserSpec {
   public:
    // TODO: initialize from a table
    ParserSpec() {
    }
    LeftInfo* LookupLed(Id_t id);  // int is Id_t
    NullInfo* LookupNud(Id_t id);
  };

}  // namespace tdop

namespace arith_parse {
using tdop::TdopParser;
arith_expr_t* NullIncDec(TdopParser* p, word_t* w, int bp);
arith_expr_t* NullUnaryPlus(TdopParser* p, word_t* t, int bp);
arith_expr_t* NullUnaryMinus(TdopParser* p, word_t* t, int bp);
arith_expr_t* LeftIncDec(TdopParser* p, word_t* w, arith_expr_t* left, int rbp);
arith_expr_t* LeftIndex(TdopParser* p, word_t* w, arith_expr_t* left, int unused_bp);
arith_expr_t* LeftTernary(TdopParser* p, word_t* t, arith_expr_t* left, int bp);
};

namespace arith_spec {

extern tdop::ParserSpec kArithSpec;

inline tdop::ParserSpec* Spec() {
  return &kArithSpec;
}

// Generated tables
extern tdop::LeftInfo kLeftLookup[];
extern tdop::NullInfo kNullLookup[];

}  // namespace arith_spec

#endif  // ARITH_SPEC_H
