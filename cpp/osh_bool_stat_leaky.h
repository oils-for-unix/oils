// osh_bool_stat_leaky.h

#ifndef OSH_BOOL_STAT_H
#define OSH_BOOL_STAT_H

#include "_build/cpp/syntax_asdl.h"
#include "mycpp/mylib_leaky.h"

namespace bool_stat {

namespace Id = id_kind_asdl::Id;
using syntax_asdl::word_t;

bool isatty(Str* fd_str, word_t* blame_word);
bool DoUnaryOp(Id_t op_id, Str* s);
bool DoBinaryOp(Id_t op_id, Str* s1, Str* s2);

}  // namespace bool_stat

#endif  // OSH_BOOL_STAT_H
