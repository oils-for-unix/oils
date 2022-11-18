// frontend_match.cc: manual port of frontend/match

#include "frontend_match.h"

// This order is required to get it to compile, despite clang-format
// clang-format off
#include "_gen/frontend/types.asdl_c.h"
#include "_gen/frontend/id_kind.asdl_c.h"
#include "_gen/frontend/match.re2c.h"
// clang-format on

namespace match {

Tuple2<Id_t, int> OneToken(lex_mode_t lex_mode, Str* line, int start_pos) {
  NO_ROOTS_FRAME(FUNC_NAME);  // No allocations here
  int id;
  int end_pos;

  // TODO: get rid of these casts
  MatchOshToken(static_cast<int>(lex_mode),
                reinterpret_cast<const unsigned char*>(line->data_), len(line),
                start_pos, &id, &end_pos);
  return Tuple2<Id_t, int>(static_cast<Id_t>(id), end_pos);
}

Tuple2<Id_t, Str*> SimpleLexer::Next() {
  NO_ROOTS_FRAME(FUNC_NAME);  // NewStr() handles it
  int id;
  int end_pos;
  match_func_(reinterpret_cast<const unsigned char*>(s_->data_), len(s_), pos_,
              &id, &end_pos);

  int len = end_pos - pos_;
  Str* val = NewStr(len);
  memcpy(val->data_, s_->data_ + pos_, len);  // copy the list item
  val->data_[len] = '\0';

  pos_ = end_pos;
  return Tuple2<Id_t, Str*>(static_cast<Id_t>(id), val);
}

namespace Id = id_kind_asdl::Id;

List<Tuple2<Id_t, Str*>*>* SimpleLexer::Tokens() {
  RootsFrame _r{FUNC_NAME};
  auto tokens = NewList<Tuple2<Id_t, Str*>*>();
  while (true) {
    // Next() will handle rooting into outer scope. Other allocations are
    // retained through `tokens`
    NO_ROOTS_FRAME(LOOP);
    auto tup2 = Next();
    if (tup2.at0() == Id::Eol_Tok) {
      break;
    }
    // it's annoying that we have to put it on the heap
    tokens->append(Alloc<Tuple2<Id_t, Str*>>(tup2.at0(), tup2.at1()));
  }
  return tokens;
}

SimpleLexer* BraceRangeLexer(Str* s) {
  NO_ROOTS_FRAME(FUNC_NAME);  // Alloc() handles it
  return Alloc<SimpleLexer>(&MatchBraceRangeToken, s);
}

SimpleLexer* GlobLexer(Str* s) {
  NO_ROOTS_FRAME(FUNC_NAME);  // Alloc() handles it
  return Alloc<SimpleLexer>(&MatchGlobToken, s);
}

SimpleLexer* EchoLexer(Str* s) {
  NO_ROOTS_FRAME(FUNC_NAME);  // Alloc() handles it
  return Alloc<SimpleLexer>(&MatchEchoToken, s);
}

List<Tuple2<Id_t, Str*>*>* HistoryTokens(Str* s) {
  NO_ROOTS_FRAME(FUNC_NAME);  // No allocations here
  SimpleLexer lexer(&MatchHistoryToken, s);
  return lexer.Tokens();
}

List<Tuple2<Id_t, Str*>*>* Ps1Tokens(Str* s) {
  NO_ROOTS_FRAME(FUNC_NAME);  // No allocations here
  SimpleLexer lexer(&MatchPS1Token, s);
  return lexer.Tokens();
}

Id_t BracketUnary(Str* s) {
  NO_ROOTS_FRAME(FUNC_NAME);  // No allocations here
  return ::BracketUnary(reinterpret_cast<const unsigned char*>(s->data_),
                        len(s));
}
Id_t BracketBinary(Str* s) {
  NO_ROOTS_FRAME(FUNC_NAME);  // No allocations here
  return ::BracketBinary(reinterpret_cast<const unsigned char*>(s->data_),
                         len(s));
}
Id_t BracketOther(Str* s) {
  NO_ROOTS_FRAME(FUNC_NAME);  // No allocations here
  return ::BracketOther(reinterpret_cast<const unsigned char*>(s->data_),
                        len(s));
}

bool IsValidVarName(Str* s) {
  NO_ROOTS_FRAME(FUNC_NAME);  // No allocations here
  return ::IsValidVarName(reinterpret_cast<const unsigned char*>(s->data_),
                          len(s));
}

bool ShouldHijack(Str* s) {
  NO_ROOTS_FRAME(FUNC_NAME);  // No allocations here
  return ::ShouldHijack(reinterpret_cast<const unsigned char*>(s->data_),
                        len(s));
}

}  // namespace match
