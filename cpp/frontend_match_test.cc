#include "frontend_match.h"
#include "id.h"

#include "runtime_asdl.h"  // for cell

int main(int argc, char** argv) {
  match::SimpleLexer* lex = match::BraceRangeLexer(new Str("{-1..22}"));

  while (true) {
    auto t = lex->Next();
    int id = t.at0();
    if (id == id__Eol_Tok) {
      break;
    }
    log("id = %d", id);
    log("val = %s", t.at1()->data_);
  }

  // Similar to native/fastlex_test.py.  Just test that it matched
  assert(match::MatchOption(new Str("")) == 0);
  assert(match::MatchOption(new Str("pipefail")) > 0);
  assert(match::MatchOption(new Str("pipefai")) == 0);
  assert(match::MatchOption(new Str("pipefail_")) == 0);

  assert(match::MatchBuiltin(new Str("")) == 0);
  assert(match::MatchBuiltin(new Str("echo")) > 0);
  assert(match::MatchBuiltin(new Str("ech")) == 0);
  assert(match::MatchBuiltin(new Str("echo_")) == 0);

  // Without sed hack, it's 24 bytes because we have tag (2), id (4), val,
  // span_id.
  // Now 16 bytes.
  log("sizeof(Token) = %d", sizeof(syntax_asdl::Token));

  // Without sed hack, it's 12 bytes for tag (2) id (4) and span_id (4).
  // Now 8 bytes.
  log("sizeof(speck) = %d", sizeof(syntax_asdl::speck));

  // 16 bytes: 2 byte tag + 3 integer fields
  log("sizeof(line_span) = %d", sizeof(syntax_asdl::line_span));

  // Reordered to be 16 bytes
  log("sizeof(cell) = %d", sizeof(runtime_asdl::cell));

  // 16 bytes: pointer and length
  log("sizeof(Str) = %d", sizeof(Str));

  // 24 bytes: std::vector
  log("sizeof(List<int>) = %d", sizeof(List<int>));
  log("sizeof(List<Str*>) = %d", sizeof(List<Str*>));
}
