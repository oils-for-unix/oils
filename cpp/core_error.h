// Replacement for core/error

#ifndef CORE_ERROR_H
#define CORE_ERROR_H

#include "mylib.h"

#include "syntax_asdl.h"

namespace runtime {
extern int NO_SPID;
}

namespace error {

using syntax_asdl::Token;
using syntax_asdl::word_part_t;
using syntax_asdl::word_t;

class Usage : public std::exception {
 public:
  Usage(Str* msg, int span_id) : msg(msg), span_id(span_id) {
  }

  Str* msg;
  int span_id;
};

// This definition is different in Python than C++.  Not worth auto-translating.
class _ErrorWithLocation : public std::exception {
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
  _ErrorWithLocation(Str* user_str, int span_id, int exit_status,
                     bool show_code)
      : user_str_(user_str),
        span_id(span_id),
        token(nullptr),
        part(nullptr),
        word(nullptr),
        exit_status(exit_status),
        show_code(show_code) {
  }

  Str* UserErrorString() {
    return user_str_;
  }

  bool HasLocation() {
    return false;  // TODO: fix this
    assert(0);
  }

  int ExitStatus() {
    return 1;  // TODO: fix this
    assert(0);
  }

  Str* user_str_;
  int span_id;
  syntax_asdl::Token* token;
  syntax_asdl::word_part_t* part;
  syntax_asdl::word_t* word;

  int exit_status;
  bool show_code;
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

class RedirectEval : public _ErrorWithLocation {
 public:
  // code only uses this variant
  RedirectEval(Str* user_str, word_t* word)
      : _ErrorWithLocation(user_str, word) {
  }
};

class FailGlob : public _ErrorWithLocation {
 public:
  // code only uses this variant
  FailGlob(Str* user_str, int span_id) : _ErrorWithLocation(user_str, span_id) {
  }
};

class FatalRuntime : public _ErrorWithLocation {
 public:
  FatalRuntime(Str* user_str) : _ErrorWithLocation(user_str, -1) {
  }
  FatalRuntime(Str* user_str, int span_id, int status)
      : _ErrorWithLocation(user_str, span_id, status, false) {
  }
};

class Strict : public FatalRuntime {
 public:
  Strict(Str* user_str) : FatalRuntime(user_str) {
  }
};

// Stub
class ErrExit : public _ErrorWithLocation {
 public:
  ErrExit(Str* user_str, int span_id, int status)
      : _ErrorWithLocation(user_str, span_id, status, false) {
  }
  ErrExit(Str* user_str, int span_id, int status, bool show_code)
      : _ErrorWithLocation(user_str, span_id, status, show_code) {
  }
};

// Stub: the parts that raise aren't translated
class Expr : public _ErrorWithLocation {
#if 0
 public:
  Expr(Str* user_str, int span_id)
      : _ErrorWithLocation(user_str, span_id) {
  }
  Expr(Str* user_str, Token* token)
      : _ErrorWithLocation(user_str, token) {
  }
#endif
};

// Stub
class Runtime : public _ErrorWithLocation {
 public:
  Runtime(Str* user_str) : _ErrorWithLocation(user_str, -1) {
  }
};

}  // namespace error

#endif  // CORE_ERROR_H
