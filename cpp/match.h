// Replacement for frontend/match

#ifndef MATCH_H
#define MATCH_H

#include "mylib.h"

#include "id_kind_asdl.h"  // syntax.asdl depends on this
using id_kind_asdl::Id_t;  // TODO: proper ASDL modules 

#include "syntax_asdl.h"
#include "types_asdl.h"

namespace match {

using types_asdl::lex_mode_t;

Tuple2<Id_t, int>* OneToken(lex_mode_t lex_mode, Str* line, int start_pos);

// TODO:
typedef int MatchFunc;

// We have five functions of this kind:
//
// static inline void MatchEchoToken(const unsigned char* line, int line_len,
//                                   int start_pos, int* id, int* end_pos) {

class SimpleLexer {
 public:
  SimpleLexer(MatchFunc match_func, Str* s);
  // TODO: Implement and be careful about ownership
  Tuple2<Id_t, Str*>* Next();

 private:
  MatchFunc match_func_;
  Str* s_;
  int pos_;
};

SimpleLexer* BraceRangeLexer(Str* s);

}

#endif  // MATCH_H
