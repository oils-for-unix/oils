// Replacement for frontend/match

#ifndef MATCH_H
#define MATCH_H

#include "_build/cpp/id_kind_asdl.h"  // syntax.asdl depends on this
#include "mycpp/oldstl_containers.h"
using id_kind_asdl::Id_t;  // TODO: proper ASDL modules

#include "_build/cpp/syntax_asdl.h"
#include "_build/cpp/types_asdl.h"

namespace match {

using types_asdl::lex_mode_t;

// The big lexer
Tuple2<Id_t, int> OneToken(lex_mode_t lex_mode, Str* line, int start_pos);

// There are 5 secondary lexers with matchers of this type
typedef void (*MatchFunc)(const unsigned char* line, int line_len,
                          int start_pos, int* id, int* end_pos);

class SimpleLexer {
 public:
  SimpleLexer(MatchFunc match_func, Str* s)
      : match_func_(match_func), s_(s), pos_(0) {
  }
  Tuple2<Id_t, Str*> Next();
  List<Tuple2<Id_t, Str*>*>* Tokens();

 private:
  MatchFunc match_func_;
  Str* s_;
  int pos_;
};

//
// Secondary Lexers
//

SimpleLexer* BraceRangeLexer(Str* s);
SimpleLexer* GlobLexer(Str* s);
SimpleLexer* EchoLexer(Str* s);

List<Tuple2<Id_t, Str*>*>* HistoryTokens(Str* s);
List<Tuple2<Id_t, Str*>*>* Ps1Tokens(Str* s);

Id_t BracketUnary(Str* s);
Id_t BracketBinary(Str* s);
Id_t BracketOther(Str* s);

//
// Other Matching Functions
//

bool IsValidVarName(Str* s);
bool ShouldHijack(Str* s);

// StringToInt

int MatchOption(Str* s);

}  // namespace match

#endif  // MATCH_H
