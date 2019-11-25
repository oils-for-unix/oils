// osh_arith_parse.cc: Manual rewrites of some parts of osh/arith_parse

#include "osh_arith_parse.h"

namespace tdop {

LeftInfo* ParserSpec::LookupLed(Id_t id) {
  LeftInfo* result = &(arith_parse::kLeftLookup[id]);
  //assert(0);
  return result;
}

NullInfo* ParserSpec::LookupNud(Id_t id) {
  NullInfo* result = &(arith_parse::kNullLookup[id]);
  //assert(0);
  return result;
}

}  // namespace tdop

namespace arith_parse {

tdop::ParserSpec kArithSpec;

}  // namespace arith_parse
