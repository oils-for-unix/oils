// asdl_pretty.cc: Manual port of asdl/pretty

#include "asdl_pretty.h"

// This order is required to get it to compile, despite clang-format
// clang-format off
#include "osh-types.h"
#include "id.h"
#include "osh-lex.h"
// clang-format on

namespace pretty {

Str* String(Str* s) {
  if (IsPlainWord(reinterpret_cast<const unsigned char*>(s->data_), s->len_)) {
    return s;
  } else {
    return repr(s);
  }
}

}  // namespace pretty
