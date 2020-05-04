// osh_sh_expr_eval.h

#ifndef OSH_SH_EXPR_EVAL_H
#define OSH_SH_EXPR_EVAL_H

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

#endif  // OSH_SH_EXPR_EVAL_H
