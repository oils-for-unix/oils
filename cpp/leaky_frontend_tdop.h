// Replacement for osh/arith_parse

#ifndef FRONTEND_TDOP_H
#define FRONTEND_TDOP_H

#include "_build/cpp/id_kind_asdl.h"
#include "_build/cpp/syntax_asdl.h"

using id_kind_asdl::Id_t;
using syntax_asdl::arith_expr_t;
using syntax_asdl::word_t;

namespace tdop {

class TdopParser;  // forward declaration

typedef arith_expr_t* (*LeftFunc)(TdopParser*, word_t*, arith_expr_t*, int);
typedef arith_expr_t* (*NullFunc)(TdopParser*, word_t*, int);

struct LeftInfo {
  LeftFunc led;
  int lbp;
  int rbp;

  DISALLOW_COPY_AND_ASSIGN(LeftInfo)
};

struct NullInfo {
  NullFunc nud;
  int bp;

  DISALLOW_COPY_AND_ASSIGN(NullInfo)
};

class ParserSpec {
 public:
  ParserSpec() {
  }
  LeftInfo* LookupLed(Id_t id);
  NullInfo* LookupNud(Id_t id);

  DISALLOW_COPY_AND_ASSIGN(ParserSpec)
};

}  // namespace tdop

#endif  // FRONTEND_TDOP_H
