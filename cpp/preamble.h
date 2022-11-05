// preamble.h: declarations to run osh_eval.cc

#include <errno.h>
#include <fcntl.h>     // e.g. F_DUPFD used directly
#include <sys/wait.h>  // e.g. WIFSIGNALED() called directly

#include "_gen/core/optview.h"
#include "_gen/core/runtime.asdl.h"
#include "_gen/frontend/arg_types.h"
#include "_gen/frontend/consts.h"
#include "_gen/frontend/id_kind.asdl.h"  // syntax.asdl depends on this
#include "_gen/frontend/option.asdl.h"
#include "_gen/frontend/signal.h"
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
#include "mycpp/runtime.h"  // runtime library e.g. with Python data structures
