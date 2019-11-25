// Replacement for osh/arith_parse

#ifndef OSH_ARITH_PARSE_H
#define OSH_ARITH_PARSE_H

#include "frontend_tdop.h"

namespace arith_parse {

extern tdop::ParserSpec kArithSpec;

inline tdop::ParserSpec* Spec() {
  return &kArithSpec;
}

// Generated tables in _devbuild/gen-cpp/
extern tdop::LeftInfo kLeftLookup[];
extern tdop::NullInfo kNullLookup[];

}  // namespace arith_parse

#endif  // OSH_ARITH_PARSE_H
