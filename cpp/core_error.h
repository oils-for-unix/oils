// Replacement for core/error

#ifndef CORE_ERROR_H
#define CORE_ERROR_H

#include "mylib.h"

#include "asdl_runtime.h"
#include "syntax_asdl.h"

namespace error {

using syntax_asdl::Token;
using syntax_asdl::word_part_t;
using syntax_asdl::word_t;

// This definition is different in Python than C++.  Not worth auto-translating.
class _ErrorWithLocation {
 public:
  _ErrorWithLocation(Str* user_str, int span_id)
      : user_str_(user_str),
        span_id(span_id),
        token(nullptr),
        part(nullptr),
        word(nullptr) {
  }
  _ErrorWithLocation(Str* user_str, Token* token)
      : user_str_(user_str),
        span_id(runtime::NO_SPID),
        token(token),
        part(nullptr),
        word(nullptr) {
  }
  _ErrorWithLocation(Str* user_str, word_part_t* part)
      : user_str_(user_str),
        span_id(runtime::NO_SPID),
        token(nullptr),
        part(part),
        word(nullptr) {
  }
  _ErrorWithLocation(Str* user_str, word_t* word)
      : user_str_(user_str),
        span_id(runtime::NO_SPID),
        token(nullptr),
        part(nullptr),
        word(word) {
  }

  Str* UserErrorString() {
    return user_str_;
  }

  Str* user_str_;
  int span_id;
  syntax_asdl::Token* token;
  syntax_asdl::word_part_t* part;
  syntax_asdl::word_t* word;
};

class Parse : public _ErrorWithLocation {
 public:
  Parse(Str* user_str, int span_id) : _ErrorWithLocation(user_str, span_id) {
  }
  Parse(Str* user_str, Token* token) : _ErrorWithLocation(user_str, token) {
  }
  Parse(Str* user_str, word_part_t* part) : _ErrorWithLocation(user_str, part) {
  }
  Parse(Str* user_str, word_t* word) : _ErrorWithLocation(user_str, word) {
  }
};

}  // namespace error

#endif  // CORE_ERROR_H
