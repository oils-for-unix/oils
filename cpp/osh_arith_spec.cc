// osh_arith_spec.cc: Manual port of osh/arith_spec

#include "osh_arith_spec.h"

namespace tdop {

LeftInfo* ParserSpec::LookupLed(Id_t id) {
  LeftInfo* result = &(arith_spec::kLeftLookup[id]);
  //assert(0);
  return result;
}

NullInfo* ParserSpec::LookupNud(Id_t id) {
  NullInfo* result = &(arith_spec::kNullLookup[id]);
  //assert(0);
  return result;
}

}  // namespace tdop

namespace arith_spec {

tdop::ParserSpec kArithSpec;

}  // namespace arith_spec
