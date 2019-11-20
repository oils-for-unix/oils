// Replacement for core/error

#ifndef CORE_ERROR_H
#define CORE_ERROR_H

#include "mylib.h"

#include "syntax_asdl.h"

namespace error {

// This definition is different in Python than C++.  Not worth auto-translating.
class _ErrorWithLocation {
 public:
  _ErrorWithLocation(Str* s, syntax_asdl::token* token)
      : token(token) {
  }
  int span_id;
  syntax_asdl::token* token;
  syntax_asdl::word_part_t* part;
  syntax_asdl::word_t* word;
};

class Parse : public _ErrorWithLocation {
 public:
  Parse(Str* s, syntax_asdl::token* token)
      : _ErrorWithLocation(s, token) {
  }
};

}  // namespace error

#endif  // CORE_ERROR_H
