// frontend_match.cc: manual port of frontend/match

#include "frontend_match.h"

// This order is required to get it to compile, despite clang-format
// clang-format off
#include "_gen/frontend/types.asdl_c.h"
#include "_gen/frontend/id_kind.asdl_c.h"
#include "_gen/frontend/match.re2c.h"
// clang-format on

namespace match {

using id_kind_asdl::Id;

Tuple2<Id_t, int> OneToken(lex_mode_t lex_mode, BigStr* line, int start_pos) {
  int id;
  int end_pos;

  // TODO: get rid of these casts
  MatchOshToken(static_cast<int>(lex_mode),
                reinterpret_cast<const unsigned char*>(line->data_), len(line),
                start_pos, &id, &end_pos);
  return Tuple2<Id_t, int>(static_cast<Id_t>(id), end_pos);
}

Tuple2<Id_t, BigStr*> SimpleLexer::Next() {
  int id;
  int end_pos;
  match_func_(reinterpret_cast<const unsigned char*>(s_->data_), len(s_), pos_,
              &id, &end_pos);

  int len = end_pos - pos_;
  BigStr* val = NewStr(len);
  memcpy(val->data_, s_->data_ + pos_, len);  // copy the list item
  val->data_[len] = '\0';

  pos_ = end_pos;
  return Tuple2<Id_t, BigStr*>(static_cast<Id_t>(id), val);
}

List<Tuple2<Id_t, BigStr*>*>* SimpleLexer::Tokens() {
  auto tokens = NewList<Tuple2<Id_t, BigStr*>*>();
  while (true) {
    auto tup2 = Next();
    if (tup2.at0() == Id::Eol_Tok) {
      break;
    }
    // it's annoying that we have to put it on the heap
    tokens->append(Alloc<Tuple2<Id_t, BigStr*>>(tup2.at0(), tup2.at1()));
  }
  return tokens;
}

Tuple2<Id_t, int> SimpleLexer2::Next() {
  int id;
  int end_pos;
  match_func_(reinterpret_cast<const unsigned char*>(s_->data_), len(s_), pos_,
              &id, &end_pos);

  pos_ = end_pos;
  return Tuple2<Id_t, int>(static_cast<Id_t>(id), end_pos);
}

List<Tuple2<Id_t, BigStr*>*>* SimpleLexer2::Tokens() {
  auto tokens = NewList<Tuple2<Id_t, BigStr*>*>();
  int pos = 0;
  while (true) {
    auto tup2 = Next();
    Id_t id = tup2.at0();
    int end_pos = tup2.at1();

    if (id == Id::Eol_Tok) {
      break;
    }
    log("pos %d end_pos %d", pos, end_pos);

    int len = end_pos - pos_;
    BigStr* tok_val = NewStr(len);
    memcpy(tok_val->data_, s_->data_ + pos_, len);  // copy the list item
    tok_val->data_[len] = '\0';

    // It's annoying that we have to put it on the heap
    tokens->append(Alloc<Tuple2<Id_t, BigStr*>>(id, tok_val));
    pos = end_pos;
  }
  return tokens;
}

SimpleLexer* BraceRangeLexer(BigStr* s) {
  return Alloc<SimpleLexer>(&MatchBraceRangeToken, s);
}

SimpleLexer* GlobLexer(BigStr* s) {
  return Alloc<SimpleLexer>(&MatchGlobToken, s);
}

SimpleLexer2* EchoLexer(BigStr* s) {
  return Alloc<SimpleLexer2>(&MatchEchoToken, s);
}

List<Tuple2<Id_t, BigStr*>*>* HistoryTokens(BigStr* s) {
  SimpleLexer lexer(&MatchHistoryToken, s);
  return lexer.Tokens();
}

List<Tuple2<Id_t, BigStr*>*>* Ps1Tokens(BigStr* s) {
  SimpleLexer lexer(&MatchPS1Token, s);
  return lexer.Tokens();
}

Id_t BracketUnary(BigStr* s) {
  return ::BracketUnary(reinterpret_cast<const unsigned char*>(s->data_),
                        len(s));
}
Id_t BracketBinary(BigStr* s) {
  return ::BracketBinary(reinterpret_cast<const unsigned char*>(s->data_),
                         len(s));
}
Id_t BracketOther(BigStr* s) {
  return ::BracketOther(reinterpret_cast<const unsigned char*>(s->data_),
                        len(s));
}

bool IsValidVarName(BigStr* s) {
  return ::IsValidVarName(reinterpret_cast<const unsigned char*>(s->data_),
                          len(s));
}

bool ShouldHijack(BigStr* s) {
  return ::ShouldHijack(reinterpret_cast<const unsigned char*>(s->data_),
                        len(s));
}

bool LooksLikeFloat(BigStr* s) {
  return ::LooksLikeFloat(reinterpret_cast<const unsigned char*>(s->data_),
                          len(s));
}

bool LooksLikeInteger(BigStr* s) {
  return ::LooksLikeInteger(reinterpret_cast<const unsigned char*>(s->data_),
                            len(s));
}

}  // namespace match
