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
#include "cpp/core.h"
#include "cpp/core_error.h"
#include "cpp/core_pyerror.h"
#include "cpp/fanos.h"
#include "cpp/frontend_flag_spec.h"
#include "cpp/frontend_match.h"
#include "cpp/frontend_pyreadline.h"
#include "cpp/libc.h"
#include "cpp/osh.h"
#include "cpp/osh_tdop.h"
#include "cpp/pgen2.h"
#include "cpp/pylib.h"
#include "cpp/qsn.h"
#include "cpp/stdlib.h"
#include "cpp/translation_stubs.h"
#include "mycpp/runtime.h"  // runtime library e.g. with Python data structures
