// osh.h

#ifndef LEAKY_OSH_H
#define LEAKY_OSH_H

#include "_gen/frontend/syntax.asdl.h"
#include "cpp/osh_tdop.h"
#include "mycpp/runtime.h"

namespace arith_parse {

extern tdop::ParserSpec* kArithSpec;

inline tdop::ParserSpec* Spec() {
  return kArithSpec;
}

// Generated tables in _devbuild/gen-cpp/
extern tdop::LeftInfo kLeftLookup[];
extern tdop::NullInfo kNullLookup[];

}  // namespace arith_parse

namespace bool_stat {

using syntax_asdl::word_t;

bool isatty(BigStr* fd_str, word_t* blame_word);
bool DoUnaryOp(Id_t op_id, BigStr* s);
bool DoBinaryOp(Id_t op_id, BigStr* s1, BigStr* s2);

}  // namespace bool_stat

namespace sh_expr_eval {

inline bool IsLower(BigStr* ch) {
  assert(len(ch) == 1);
  uint8_t c = ch->data_[0];
  return ('a' <= c && c <= 'z');
}

inline bool IsUpper(BigStr* ch) {
  assert(len(ch) == 1);
  uint8_t c = ch->data_[0];
  return ('A' <= c && c <= 'Z');
}

}  // namespace sh_expr_eval

#endif  // LEAKY_OSH_H
