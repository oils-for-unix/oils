#include "osh.h"  // for arith_parse

// This code structure is odd because frontend/tdop.py would allow multiple
// TDOP parser.  Since we only have one, we just hard-code it in C++.

namespace tdop {

LeftInfo* ParserSpec::LookupLed(Id_t id) {
  return &(arith_parse::kLeftLookup[id]);
}

NullInfo* ParserSpec::LookupNud(Id_t id) {
  return &(arith_parse::kNullLookup[id]);
}

}  // namespace tdop
