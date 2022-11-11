#include "_gen/frontend/id_kind.asdl_c.h"
#include "cpp/leaky_frontend_match.h"
#include "vendor/greatest.h"

namespace Id = id_kind_asdl::Id;

TEST match_test() {
  match::SimpleLexer* lex = match::BraceRangeLexer(StrFromC("{-1..22}"));

  while (true) {
    auto t = lex->Next();
    int id = t.at0();
    if (id == id__Eol_Tok) {
      break;
    }
    log("id = %d", id);
    log("val = %s", t.at1()->data_);
  }

  match::SimpleLexer* lex2 = match::BraceRangeLexer(kEmptyString);
  auto t = lex2->Next();
  int id = t.at0();
  ASSERT_EQ(Id::Eol_Tok, id);

  ASSERT_EQ(Id::BoolUnary_G, match::BracketUnary(StrFromC("-G")));
  ASSERT_EQ(Id::Undefined_Tok, match::BracketUnary(StrFromC("-Gz")));
  ASSERT_EQ(Id::Undefined_Tok, match::BracketUnary(StrFromC("")));

  ASSERT_EQ(Id::BoolBinary_NEqual, match::BracketBinary(StrFromC("!=")));
  ASSERT_EQ(Id::Undefined_Tok, match::BracketBinary(StrFromC("")));

  // This still works, but can't it overflow a buffer?
  Str* s = StrFromC("!= ");
  Str* stripped = s->strip();

  ASSERT_EQ(3, len(s));
  ASSERT_EQ(2, len(stripped));

  ASSERT_EQ(Id::BoolBinary_NEqual, match::BracketBinary(stripped));

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(match_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
