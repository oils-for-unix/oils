// leaky_osh_bool_stat.h

#ifndef OSH_BOOL_STAT_H
#define OSH_BOOL_STAT_H

#include "_build/cpp/syntax_asdl.h"
#include "mycpp/mylib_leaky.h"

namespace bool_stat {

using syntax_asdl::word_t;

bool isatty(Str* fd_str, word_t* blame_word);
bool DoUnaryOp(Id_t op_id, Str* s);
bool DoBinaryOp(Id_t op_id, Str* s1, Str* s2);

}  // namespace bool_stat

namespace sh_expr_eval {

// TODO: Should refactor for int/char-based processing

inline bool IsLower(Str* ch) {
  assert(ch->len_ == 1);
  uint8_t c = ch->data_[0];
  return ('a' <= c && c <= 'z');
}

inline bool IsUpper(Str* ch) {
  assert(ch->len_ == 1);
  uint8_t c = ch->data_[0];
  return ('A' <= c && c <= 'Z');
}

}  // namespace sh_expr_eval

#endif  // OSH_BOOL_STAT_H
