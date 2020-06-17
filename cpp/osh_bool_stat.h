// osh_bool_stat.h

#ifndef OSH_BOOL_STAT_H
#define OSH_BOOL_STAT_H

#include "mylib.h"
#include "syntax_asdl.h"

namespace bool_stat {

using syntax_asdl::word_t;

inline bool isatty(int fd, Str* s, word_t* blame_word) {
  assert(0);
}

inline bool DoUnaryOp(Id_t op_id, Str* s) {
  assert(0);
}

inline bool DoBinaryOp(Id_t op_id, Str* s1, Str* s2) {
  assert(0);
}

}  // namespace bool_stat

#endif  // OSH_BOOL_STAT_H
