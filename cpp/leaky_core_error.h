// Replacement for core/error

#ifndef CORE_ERROR_H
#define CORE_ERROR_H

#include "_gen/frontend/syntax.asdl.h"
#include "mycpp/runtime.h"

namespace runtime {
extern int NO_SPID;
}

namespace error {

using syntax_asdl::Token;
using syntax_asdl::word_part_t;
using syntax_asdl::word_t;

class Usage : public std::exception, Obj {
 public:
  Usage(Str* msg, int span_id);
  Usage(Str* msg);

  Str* msg;
  int span_id;
};

constexpr uint16_t maskof_Usage() {
  return maskbit(offsetof(Usage, msg));
}

// This definition is different in Python than C++.  Not worth auto-translating.
class _ErrorWithLocation : public std::exception, Obj {
 public:
  _ErrorWithLocation(Str* user_str, int span_id);
  _ErrorWithLocation(Str* user_str, Token* token);
  _ErrorWithLocation(Str* user_str, word_part_t* part);
  _ErrorWithLocation(Str* user_str, word_t* word);
  _ErrorWithLocation(int status, Str* user_str, int span_id, bool show_code);

  Str* UserErrorString() {
    return user_str_;
  }

  bool HasLocation() {
    return false;  // TODO: fix this
    assert(0);
  }

  int ExitStatus() {
    return status;
  }

  int status;

  Str* user_str_;
  int span_id;
  syntax_asdl::Token* token;
  syntax_asdl::word_part_t* part;
  syntax_asdl::word_t* word;

  bool show_code;
};

constexpr uint16_t maskof__ErrorWithLocation() {
  return maskbit(offsetof(_ErrorWithLocation, user_str_));
}

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
  explicit FatalRuntime(Str* user_str) : _ErrorWithLocation(user_str, -1) {
  }
  FatalRuntime(int status, Str* user_str)
      : _ErrorWithLocation(status, user_str, -1, false) {
  }
};

class Strict : public FatalRuntime {
 public:
  explicit Strict(Str* user_str) : FatalRuntime(user_str) {
  }
};

// Stub
class ErrExit : public _ErrorWithLocation {
 public:
  ErrExit(Str* user_str, int span_id, int status)
      : _ErrorWithLocation(status, user_str, span_id, false) {
  }
  ErrExit(Str* user_str, int span_id, int status, bool show_code)
      : _ErrorWithLocation(status, user_str, span_id, show_code) {
  }
};

// Stub: the parts that raise aren't translated
class Expr : public _ErrorWithLocation {
 public:
  Expr(Str* user_str, int span_id) : _ErrorWithLocation(user_str, span_id) {
  }
#if 0
  Expr(Str* user_str, Token* token)
      : _ErrorWithLocation(user_str, token) {
  }
#endif
};

// Stub
class Runtime : public _ErrorWithLocation {
 public:
  explicit Runtime(Str* user_str) : _ErrorWithLocation(user_str, -1) {
  }
};

}  // namespace error

#endif  // CORE_ERROR_H
