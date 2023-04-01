// Replacement for osh/arith_parse

#ifndef FRONTEND_TDOP_H
#define FRONTEND_TDOP_H

#include "_gen/frontend/id_kind.asdl.h"
#include "_gen/frontend/syntax.asdl.h"

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
  // No fields
  ParserSpec() {
  }
  LeftInfo* LookupLed(Id_t id);
  NullInfo* LookupNud(Id_t id);

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(kZeroMask, sizeof(ParserSpec));
  }

  DISALLOW_COPY_AND_ASSIGN(ParserSpec)
};

}  // namespace tdop

#endif  // FRONTEND_TDOP_H
