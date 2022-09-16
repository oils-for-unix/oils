// leaky_preamble.h: declarations to run osh_eval.cc

// clang-format off
#include "mycpp/myerror.h"     // do this before 'errno' macro is defined
// clang-format on

#include <errno.h>
#include <fcntl.h>     // F_DUPFD used directly
#include <sys/wait.h>  // WIFSIGNALED, etc. called DIRECTLY

#include "_gen/frontend/id_kind.asdl.h"  // syntax.asdl depends on this
using id_kind_asdl::Id_t;  // TODO: proper ASDL modules may eliminate this
using id_kind_asdl::Kind_t;

#include "_gen/core/optview.h"
#include "_gen/core/runtime.asdl.h"
#include "_gen/frontend/arg_types.h"
#include "_gen/frontend/consts.h"
#include "_gen/frontend/option.asdl.h"
#include "_gen/frontend/syntax.asdl.h"
#include "_gen/frontend/types.asdl.h"
#include "_gen/oil_lang/grammar_nt.h"
#include "cpp/leaky_core.h"
#include "cpp/leaky_core_error.h"
#include "cpp/leaky_core_pyerror.h"
#include "cpp/leaky_frontend_flag_spec.h"
#include "cpp/leaky_frontend_match.h"
#include "cpp/leaky_frontend_tdop.h"
#include "cpp/leaky_libc.h"
#include "cpp/leaky_osh.h"
#include "cpp/leaky_osh_eval_stubs.h"
#include "cpp/leaky_pgen2.h"
#include "cpp/leaky_pylib.h"
#include "cpp/leaky_stdlib.h"
#include "cpp/qsn.h"
#include "cpp/segfault_handler.h"
#include "mycpp/runtime.h"  // runtime library e.g. with Python data structures

#undef errno  // for e->errno to work; see mycpp/myerror.h

inline bool are_equal(id_kind_asdl::Kind left, id_kind_asdl::Kind right) {
  return left == right;
}

// Hack for now.  Every sum type should have repr()?
inline Str* repr(syntax_asdl::source_t* obj) {
  /* NotImplemented(); */
  return StrFromC("TODO");
}

// STUB for osh/word_.py
inline Str* str(syntax_asdl::word_t* w) {
  /* NotImplemented(); */
  return StrFromC("TODO");
}
