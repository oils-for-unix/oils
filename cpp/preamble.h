// preamble.h: declarations to run osh_eval.cc

#include <sys/wait.h>    // WIFSIGNALED, etc. called DIRECTLY
#include "dumb_alloc.h"  // change the allocator
// TODO: Need #if GC
#include "mylib.h"  // runtime library e.g. with Python data structures

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
//#include "core_process.h"
#include "core_pyerror.h"
#include "core_pyos.h"
#include "core_pyutil.h"
#include "errno_.h"
#include "fcntl_.h"
#include "frontend_flag_spec.h"
#include "frontend_match.h"
#include "frontend_tdop.h"
#include "libc.h"
#include "osh_arith_parse.h"
#include "osh_bool_stat.h"
#include "osh_sh_expr_eval.h"
#include "pgen2_parse.h"
#include "posix.h"
#include "pylib_path_stat.h"
#include "qsn_qsn.h"
#include "signal_.h"
#include "time_.h"

#ifdef OSH_EVAL
#include "osh_eval_stubs.h"
#endif

// Stubs for Python exceptions.  TODO: Move more to mylib?

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
inline Str* repr(syntax_asdl::source_t* obj) {
  return new Str("TODO");
}

// STUB for osh/word_.py
inline Str* str(syntax_asdl::word_t* w) {
  return new Str("TODO");
}

// For hnode::External in asdl/format.py
inline Str* repr(void* obj) {
  return new Str("TODO: repr()");
}
