#include "id_kind_asdl.h"  // syntax.asdl depends on this

using id_kind_asdl::Id_t;  // TODO: proper ASDL modules may eliminate this
using id_kind_asdl::Kind_t;

#include "option_asdl.h"
#include "runtime_asdl.h"
#include "syntax_asdl.h"
#include "types_asdl.h"

// _build/cpp
#include "core_optview.h"
#include "grammar_nt.h"
#include "consts.h"

// oil/cpp
#include "asdl_pretty.h"
#include "core_error.h"
#include "frontend_match.h"
#include "frontend_tdop.h"
#include "osh_arith_parse.h"
// added for osh_eval
#include "core_passwd.h"
#include "osh_bool_stat.h"
#include "pylib_os_path.h"
#include "pylib_path_stat.h"
#include "libc.h"
#include "posix.h"

#ifdef OSH_EVAL
#include "osh_eval_stubs.h"
#endif

// Stubs for Python exceptions.  TODO: Move to mylib if they're used?

// e.g. libc::regex_match raises it
class RuntimeError {
 public:
  Str* message;
};

class ValueError {};

class KeyboardInterrupt {};

// Hack for now.  Every sum type should have repr()?
Str* repr(syntax_asdl::source_t* obj) {
  return new Str("TODO");
}

// STUB for osh/word_.py
Str* str(syntax_asdl::word_t* w) {
  return new Str("TODO");
}

// For hnode::External in asdl/format.py
Str* repr(void* obj) {
  return new Str("TODO: repr()");
}

// STUBS for p_die()
// [[noreturn]] avoids warnings
[[noreturn]] void p_die(Str* s, int span_id) {
  throw new error::Parse(s, span_id);
}

[[noreturn]] void p_die(Str* s, syntax_asdl::Token* token) {
  throw new error::Parse(s, token);
}

[[noreturn]] void p_die(Str* s, syntax_asdl::word_part_t* part) {
  throw new error::Parse(s, part);
}

[[noreturn]] void p_die(Str* s, syntax_asdl::word_t* w) {
  throw new error::Parse(s, w);
}

[[noreturn]] void e_die(Str* s) {
  assert(0);
}

[[noreturn]] void e_die(Str* s, int span_id) {
  assert(0);
}

[[noreturn]] void e_die(Str* s, syntax_asdl::Token* token) {
  assert(0);
}

[[noreturn]] void e_die(Str* s, syntax_asdl::word_part_t* part) {
  assert(0);
}

[[noreturn]] void e_die(Str* s, syntax_asdl::word_t* w) {
  assert(0);
}

[[noreturn]] void e_strict(Str* s, int span_id) {
  assert(0);
}

[[noreturn]] void e_strict(Str* s, syntax_asdl::Token* token) {
  assert(0);
}

[[noreturn]] void e_strict(Str* s, syntax_asdl::word_part_t* part) {
  assert(0);
}

[[noreturn]] void e_strict(Str* s, syntax_asdl::word_t* w) {
  assert(0);
}

// Used without args in osh/string_ops.py
[[noreturn]] void e_strict(Str* s) {
  assert(0);
}

// e.g. used in core/state.py
[[noreturn]] void e_usage(Str* s) {
  assert(0);
}
