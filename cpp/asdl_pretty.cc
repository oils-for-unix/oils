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
  } else {
    return repr(s);
  }
}

}  // namespace pretty

