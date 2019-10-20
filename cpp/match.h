#ifndef MATCH_H
#define MATCH_H

#include "mylib.h"

#include "id_kind_asdl.h"  // syntax.asdl depends on this
using id_kind_asdl::Id_t;  // TODO: proper ASDL modules 

#include "syntax_asdl.h"
#include "types_asdl.h"

void p_die(Str* fmt, syntax_asdl::token* blame_token);

namespace match {

using types_asdl::lex_mode_t;

Tuple2<Id_t, int>* OneToken(lex_mode_t lex_mode, Str* line, int start_pos);
}

#endif  // MATCH_H
