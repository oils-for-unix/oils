// examples/varargs_preamble.h

#include <exception>

#include "mycpp/runtime.h"

//
// Copied from cpp/core_error.h
//

namespace error {

class _ErrorWithLocation : public std::exception {
 public:
  _ErrorWithLocation(BigStr* user_str, int span_id) {
  }
};

class Parse : public _ErrorWithLocation {
 public:
  Parse(BigStr* user_str, int span_id) : _ErrorWithLocation(user_str, span_id) {
  }
};

class FatalRuntime : public _ErrorWithLocation {
 public:
  FatalRuntime(BigStr* user_str) : _ErrorWithLocation(user_str, -1) {
  }
};

};

//
// Copied from cpp/core_pyerror.h
//

[[noreturn]] inline void p_die(BigStr* s, int span_id) {
  throw new error::Parse(s, span_id);
}

[[noreturn]] inline void e_die(BigStr* s) {
  throw new error::FatalRuntime(s);
}

[[noreturn]] inline void e_die(BigStr* s, int span_id) {
  throw new error::FatalRuntime(s);
}
