#include "cpp/frontend_match.h"

#include "_gen/frontend/id_kind.asdl_c.h"
#include "vendor/greatest.h"

using id_kind_asdl::Id;

TEST lexer_test() {
  // Need lex_mode_e
  // auto tup = match::OneToken(lex_mode__ShCommand, StrFromC("cd /tmp"), 0);

  match::SimpleLexer* lex = match::BraceRangeLexer(StrFromC("{-1..22}"));

  List<Tuple2<Id_t, Str*>*>* toks = lex->Tokens();
  for (int i = 0; i < len(toks); i++) {
    auto* t = toks->index_(i);
    int id = t->at0();
    if (id == id__Eol_Tok) {
      break;
    }
    log("id = %d", id);
    log("val = %s", t->at1()->data_);
  }

  match::SimpleLexer* lex2 = match::BraceRangeLexer(kEmptyString);
  auto t = lex2->Next();
  int id = t.at0();
  ASSERT_EQ(Id::Eol_Tok, id);

  PASS();
}

TEST func_test() {
  ASSERT_EQ(Id::BoolUnary_G, match::BracketUnary(StrFromC("-G")));
  ASSERT_EQ(Id::Undefined_Tok, match::BracketUnary(StrFromC("-Gz")));
  ASSERT_EQ(Id::Undefined_Tok, match::BracketUnary(StrFromC("")));

  ASSERT_EQ(Id::BoolBinary_NEqual, match::BracketBinary(StrFromC("!=")));
  ASSERT_EQ(Id::Undefined_Tok, match::BracketBinary(StrFromC("")));

  ASSERT_EQ(Id::Op_LParen, match::BracketOther(StrFromC("(")));

  // This still works, but can't it overflow a buffer?
  Str* s = StrFromC("!= ");
  Str* stripped = s->strip();

  ASSERT_EQ(3, len(s));
  ASSERT_EQ(2, len(stripped));

  ASSERT_EQ(Id::BoolBinary_NEqual, match::BracketBinary(stripped));

  ASSERT(match::IsValidVarName(StrFromC("a")));
  ASSERT(!match::IsValidVarName(StrFromC("01")));
  ASSERT(!match::IsValidVarName(StrFromC("!!")));
  ASSERT(!match::IsValidVarName(kEmptyString));

  ASSERT(match::ShouldHijack(StrFromC("#!/bin/bash\n")));
  ASSERT(!match::ShouldHijack(StrFromC("/bin/bash\n")));

  PASS();
}

TEST for_test_coverage() {
  (void)match::GlobLexer(kEmptyString);
  (void)match::EchoLexer(kEmptyString);
  (void)match::HistoryTokens(kEmptyString);
  (void)match::Ps1Tokens(kEmptyString);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(lexer_test);
  RUN_TEST(func_test);
  RUN_TEST(for_test_coverage);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
