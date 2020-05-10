#include "id_kind_asdl.h"  // syntax.asdl depends on this

using id_kind_asdl::Id_t;  // TODO: proper ASDL modules may eliminate this
using id_kind_asdl::Kind_t;

#include "option_asdl.h"
#include "runtime_asdl.h"
#include "syntax_asdl.h"
#include "types_asdl.h"

// _build/cpp
#include "arg_types.h"
#include "consts.h"
#include "core_optview.h"
#include "grammar_nt.h"

// oil/cpp
#include "core_error.h"
#include "frontend_arg_def.h"
#include "frontend_match.h"
#include "frontend_tdop.h"
#include "osh_arith_parse.h"
#include "osh_sh_expr_eval.h"
#include "pgen2_parse.h"
#include "qsn_qsn.h"
// added for osh_eval
#include "core_passwd.h"
#include "libc.h"
#include "osh_bool_stat.h"
#include "posix.h"
#include "pylib_os_path.h"
#include "pylib_path_stat.h"

#ifdef OSH_EVAL
#include "osh_eval_stubs.h"
#endif

// Stubs for Python exceptions.  TODO: Move to mylib if they're used?

// e.g. libc::regex_match raises it
class RuntimeError {
 public:
  Str* message;
};

// TODO: remove this.  cmd_eval.py RunOilProc uses it, which we probably
// don't need
class TypeError {
 public:
  TypeError(Str* arg) {
    assert(0);
  }
};

class KeyboardInterrupt {};

class SystemExit {
 public:
  SystemExit(int status) : status_(status) {
  }
  int status_;
};

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
  throw new error::FatalRuntime(s);
}

[[noreturn]] void e_die(Str* s, int span_id) {
  throw new error::FatalRuntime(s);
}

[[noreturn]] void e_die(Str* s, syntax_asdl::Token* token) {
  throw new error::FatalRuntime(s);
}

[[noreturn]] void e_die(Str* s, syntax_asdl::word_part_t* part) {
  throw new error::FatalRuntime(s);
}

[[noreturn]] void e_die(Str* s, syntax_asdl::word_t* w) {
  throw new error::FatalRuntime(s);
}

[[noreturn]] void e_strict(Str* s, int span_id) {
  throw new error::Strict(s);
}

[[noreturn]] void e_strict(Str* s, syntax_asdl::Token* token) {
  throw new error::Strict(s);
}

[[noreturn]] void e_strict(Str* s, syntax_asdl::word_part_t* part) {
  throw new error::Strict(s);
}

[[noreturn]] void e_strict(Str* s, syntax_asdl::word_t* w) {
  throw new error::Strict(s);
}

// Used without args in osh/string_ops.py
[[noreturn]] void e_strict(Str* s) {
  throw new error::Strict(s);
}

// e.g. used in core/state.py
[[noreturn]] void e_usage(Str* s) {
  throw new error::Usage(s, -1);  // NO_SPID
}

[[noreturn]] void e_usage(Str* s, int span_id) {
  throw new error::Usage(s, span_id);
}
