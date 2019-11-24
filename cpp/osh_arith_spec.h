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
    // TODO: initialize from a table
    ParserSpec() {
    }
    LeftInfo* LookupLed(Id_t id);  // int is Id_t
    NullInfo* LookupNud(Id_t id);
  };

}  // namespace tdop

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
