// core_error.h: Corresponds to for core/error.py

#ifndef CORE_ERROR_H
#define CORE_ERROR_H

#include "_gen/frontend/syntax.asdl.h"
#include "mycpp/runtime.h"

namespace error {

namespace loc = syntax_asdl::loc;

// This definition is different in Python than C++.  Not worth auto-translating.
class _ErrorWithLocation {
 public:
  _ErrorWithLocation(Str* user_str, syntax_asdl::loc_t* location)
      : GC_CLASS_FIXED(header_, field_mask(), sizeof(_ErrorWithLocation)),
        user_str_(user_str),
        location(location) {
  }

  Str* UserErrorString() {
    return user_str_;
  }

  bool HasLocation() {
    return false;  // TODO: fix this
    assert(0);
  }

  GC_OBJ(header_);

  Str* user_str_;
  syntax_asdl::loc_t* location;

  static constexpr uint16_t field_mask() {
    return maskbit(offsetof(_ErrorWithLocation, user_str_)) |
           maskbit(offsetof(_ErrorWithLocation, location));
  }
};

class Parse : public _ErrorWithLocation {
 public:
  Parse(Str* user_str, syntax_asdl::loc_t* location)
      : _ErrorWithLocation(user_str, location) {
  }
};

class RedirectEval : public _ErrorWithLocation {
 public:
  // code only uses this variant
  RedirectEval(Str* user_str, syntax_asdl::loc_t* location)
      : _ErrorWithLocation(user_str, location) {
  }
};

class FailGlob : public _ErrorWithLocation {
 public:
  // code only uses this variant
  FailGlob(Str* user_str, syntax_asdl::loc_t* location)
      : _ErrorWithLocation(user_str, location) {
  }
};

class FatalRuntime : public _ErrorWithLocation {
 public:
  FatalRuntime(int exit_status, Str* user_str, syntax_asdl::loc_t* location)
      : _ErrorWithLocation(user_str, location), exit_status(exit_status) {
  }
  int ExitStatus() {
    return exit_status;
  }

  int exit_status;
};

class Strict : public FatalRuntime {
 public:
  explicit Strict(Str* user_str, syntax_asdl::loc_t* location)
      : FatalRuntime(1, user_str, location) {
  }
};

// Stub
class ErrExit : public FatalRuntime {
 public:
  ErrExit(int status, Str* user_str, syntax_asdl::loc_t* location)
      : FatalRuntime(status, user_str, location) {
  }
  ErrExit(int status, Str* user_str, syntax_asdl::loc_t* location,
          bool show_code)
      : FatalRuntime(status, user_str, location) {
  }
  bool show_code;
};

// Stub: the parts that raise aren't translated
class Expr : public FatalRuntime {
 public:
  Expr(Str* user_str, syntax_asdl::loc_t* location)
      : FatalRuntime(3, user_str, location) {
  }
};

// Stub
class Runtime : public _ErrorWithLocation {
 public:
  explicit Runtime(Str* user_str)
      : _ErrorWithLocation(user_str, Alloc<loc::Span>(-1)) {
  }
};

}  // namespace error

#endif  // CORE_ERROR_H
