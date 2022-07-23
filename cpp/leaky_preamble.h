// leaky_preamble.h: declarations to run osh_eval.cc

// clang-format off
#include "mycpp/myerror.h"     // do this before 'errno' macro is defined
// clang-format on

#include <errno.h>
#include <fcntl.h>     // F_DUPFD used directly
#include <sys/wait.h>  // WIFSIGNALED, etc. called DIRECTLY

#include "leaky_dumb_alloc.h"  // change the allocator
// TODO: Need #if GC
#include "_build/cpp/id_kind_asdl.h"  // syntax.asdl depends on this
#include "mycpp/mylib_old.h"  // runtime library e.g. with Python data structures

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
#include "leaky_core_error.h"
//#include "core_process.h"
#include "leaky_core.h"
#include "leaky_core_pyerror.h"
#include "leaky_frontend_flag_spec.h"
#include "leaky_frontend_match.h"
#include "leaky_frontend_tdop.h"
#include "leaky_libc.h"
#include "leaky_osh.h"
#include "leaky_osh_eval_stubs.h"
#include "leaky_pgen2.h"
#include "leaky_pylib.h"
#include "leaky_stdlib.h"
#include "qsn.h"
#include "segfault_handler.h"

inline bool are_equal(id_kind_asdl::Kind left, id_kind_asdl::Kind right) {
  return left == right;
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
