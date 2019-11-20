// asdl_pretty.cc: Manual port of asdl/pretty

#include "asdl_pretty.h"

// C includes have to go together
#include "id.h"
#include "osh-types.h"
#include "osh-lex.h"

namespace pretty {

Str* String(Str* s) {
  if (IsPlainWord(reinterpret_cast<const unsigned char*>(s->data_), s->len_)) {
    return s;
  }

  // TODO: Replace this STUB.
  Str* quoted = str_concat(str_concat(new Str("'"), s), new Str("'"));
  return quoted;

  // Should we write a Quoter class?
  //   - replace util.BackslashEscape().  Appends 1 or 2 chars.
  //   - replace cgi.escape().  This appends strings like &amp;, not
  //     characters.
  //
  // cpp/quote.{cc,h}
  // quote::TSV2 ?
}

}  // namespace pretty

