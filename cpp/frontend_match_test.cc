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

  log("hello");
}
