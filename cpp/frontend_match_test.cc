#include "frontend_match.h"
#include "id.h"

int main(int argc, char **argv) {
  match::SimpleLexer* lex = match::BraceRangeLexer(new Str("{-1..22}"));

  while (true) {
    auto t = lex->Next();
    int id = t->at0();
    if (id == id__Eol_Tok) {
      break;
    }
    log("id = %d", id);
    log("val = %s", t->at1()->data_);
  }

  // 24 bytes because we have tag (2), id (4), val, span_id
  // Could compress tag
  // TODO: Should be 16
  log("sizeof(Token) = %d", sizeof(syntax_asdl::Token));

  // 12 for tag (2) id (4) and span_id (4)
  // TODO: Should be 8
  log("sizeof(speck) = %d", sizeof(syntax_asdl::speck));
}
