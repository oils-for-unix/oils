// osh_arith_spec.cc: Manual port of osh/arith_spec

#include "osh_arith_spec.h"

// TODO: include generated table

namespace tdop {

LeftInfo* ParserSpec::LookupLed(Id_t id) {
  assert(0);
}

NullInfo* ParserSpec::LookupNud(Id_t id) {
  assert(0);
}

}  // namespace tdop

namespace arith_spec {

tdop::ParserSpec kArithSpec;

}  // namespace arith_spec
