// preamble_leaky.h: declarations to run osh_eval.cc

// clang-format off
#include "mycpp/myerror.h"     // do this before 'errno' macro is defined
// clang-format on

#include <errno.h>
#include <sys/wait.h>  // WIFSIGNALED, etc. called DIRECTLY

#include "dumb_alloc_leaky.h"  // change the allocator
// TODO: Need #if GC
#include "_build/cpp/id_kind_asdl.h"  // syntax.asdl depends on this
#include "mycpp/mylib_leaky.h"  // runtime library e.g. with Python data structures

using id_kind_asdl::Id_t;  // TODO: proper ASDL modules may eliminate this
using id_kind_asdl::Kind_t;

#include "_build/cpp/arg_types.h"
#include "_build/cpp/consts.h"
#include "_build/cpp/core_optview.h"
#include "_build/cpp/option_asdl.h"
#include "_build/cpp/runtime_asdl.h"
#include "_build/cpp/syntax_asdl.h"
#include "_build/cpp/types_asdl.h"
#include "_devbuild/gen/grammar_nt.h"

// oil/cpp
#include "core_error_leaky.h"
//#include "core_process.h"
#include "core_pyerror_leaky.h"
#include "core_pyos_leaky.h"
#include "core_pyutil_leaky.h"
#include "fcntl__leaky.h"
#include "frontend_flag_spec_leaky.h"
#include "frontend_match_leaky.h"
#include "frontend_tdop_leaky.h"
#include "libc_leaky.h"
#include "osh_arith_parse_leaky.h"
#include "osh_bool_stat_leaky.h"
#include "osh_sh_expr_eval_leaky.h"
#include "pgen2_parse_leaky.h"
#include "posix_leaky.h"
#include "pylib_os_path_leaky.h"
#include "pylib_path_stat_leaky.h"
#include "qsn_qsn.h"
#include "segfault_handler.h"
#include "signal__leaky.h"
#include "time__leaky.h"

#ifdef OSH_EVAL
#include "osh_eval_stubs_leaky.h"
#endif

inline bool are_equal(id_kind_asdl::Kind left, id_kind_asdl::Kind right) {
  return left == right;
  ;
}

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
