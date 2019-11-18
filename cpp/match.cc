// match.cc

#include "match.h"

// C includes have to go together
#include "id.h"
#include "osh-types.h"
#include "osh-lex.h"

namespace match {

inline Tuple2<Id_t, int>* OneToken(lex_mode_t lex_mode, Str* line, int start_pos) {
  int id;
  int end_pos;
  // TODO: get rid of these casts
  MatchOshToken(static_cast<int>(lex_mode),
                reinterpret_cast<const unsigned char*>(line->data_),
                line->len_, start_pos, &id, &end_pos);
  return new Tuple2<Id_t, int>(static_cast<Id_t>(id), end_pos);
}

// Secondary lexers

// We have five functions of this kind:
//
// static inline void MatchEchoToken(const unsigned char* line, int line_len,
//                                   int start_pos, int* id, int* end_pos) {
//
// So we could make lexers parameterized by this?
// typedef SimpleLexer<MatchEchoToken> EchoLexer;
// new EchoLexer(tok->val)

}  // namespace match

