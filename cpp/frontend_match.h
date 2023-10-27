// Replacement for frontend/match

#ifndef MATCH_H
#define MATCH_H

#include "_gen/frontend/id_kind.asdl.h"  // syntax.asdl depends on this
#include "mycpp/runtime.h"
using id_kind_asdl::Id_t;  // TODO: proper ASDL modules

#include "_gen/frontend/syntax.asdl.h"
#include "_gen/frontend/types.asdl.h"

namespace match {

using types_asdl::lex_mode_t;

// The big lexer
Tuple2<Id_t, int> OneToken(lex_mode_t lex_mode, BigStr* line, int start_pos);

// There are 5 secondary lexers with matchers of this type
typedef void (*MatchFunc)(const unsigned char* line, int line_len,
                          int start_pos, int* id, int* end_pos);

class SimpleLexer {
 public:
  SimpleLexer(MatchFunc match_func, BigStr* s)
      : match_func_(match_func), s_(s), pos_(0) {
  }

  Tuple2<Id_t, BigStr*> Next();
  List<Tuple2<Id_t, BigStr*>*>* Tokens();

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(SimpleLexer));
  }

  static constexpr uint32_t field_mask() {
    return maskbit(offsetof(SimpleLexer, s_));
  }

 private:
  MatchFunc match_func_;
  BigStr* s_;
  int pos_;
};

//
// Secondary Lexers
//

SimpleLexer* BraceRangeLexer(BigStr* s);
SimpleLexer* GlobLexer(BigStr* s);
SimpleLexer* EchoLexer(BigStr* s);

List<Tuple2<Id_t, BigStr*>*>* HistoryTokens(BigStr* s);
List<Tuple2<Id_t, BigStr*>*>* Ps1Tokens(BigStr* s);

Id_t BracketUnary(BigStr* s);
Id_t BracketBinary(BigStr* s);
Id_t BracketOther(BigStr* s);

//
// Other Matching Functions
//

bool IsValidVarName(BigStr* s);
bool ShouldHijack(BigStr* s);
bool LooksLikeFloat(BigStr* s);
bool LooksLikeInteger(BigStr* s);

// StringToInt

int MatchOption(BigStr* s);

}  // namespace match

#endif  // MATCH_H
