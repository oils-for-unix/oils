// bin/osh_parse_preamble.h: declarations to run osh_parse.mycpp

#include <errno.h>
#include <fcntl.h>         // e.g. F_DUPFD used directly
#include <fnmatch.h>       // FNM_CASEFOLD in osh/sh_expr_eval.py
#include <glob.h>          // GLOB_PERIOD in osh/glob_.py
#include <regex.h>         // REG_ICASE in osh/sh_expr_eval.py
#include <sys/resource.h>  // RLIM_INFINITY in builtin/process_osh.py
#include <sys/wait.h>      // e.g. WIFSIGNALED() called directly

#include "_gen/core/optview.h"
#include "_gen/core/runtime.asdl.h"
#include "_gen/core/value.asdl.h"
#include "_gen/data_lang/nil8.asdl.h"
#include "_gen/display/pretty.asdl.h"
#include "_gen/frontend/arg_types.h"
#include "_gen/frontend/consts.h"
#include "_gen/frontend/help_meta.h"
#include "_gen/frontend/id_kind.asdl.h"  // syntax.asdl depends on this
#include "_gen/frontend/option.asdl.h"
#include "_gen/frontend/signal.h"
#include "_gen/frontend/syntax.asdl.h"
#include "_gen/frontend/types.asdl.h"
#include "_gen/ysh/grammar_nt.h"
#include "cpp/core.h"
#include "cpp/data_lang.h"
#include "cpp/fanos.h"
#include "cpp/frontend_flag_spec.h"
#include "cpp/frontend_match.h"
#include "cpp/frontend_pyreadline.h"
#include "cpp/libc.h"
#include "cpp/osh.h"
#include "cpp/osh_tdop.h"
#include "cpp/pgen2.h"
#include "cpp/pylib.h"
#include "cpp/stdlib.h"
#include "cpp/translation_stubs.h"
#include "mycpp/runtime.h"  // runtime library e.g. with Python data structures

// Function prototypes are emitted in mycpp's DECL phase, and some of them have
// default args that reuide this.

using id_kind_asdl::Id;

using hnode_asdl::hnode;

using pretty_asdl::doc;

using runtime_asdl::cmd_value;
using runtime_asdl::part_value;
using runtime_asdl::scope_e;

using syntax_asdl::command;
using syntax_asdl::expr;
using syntax_asdl::loc;
using syntax_asdl::printf_part;  // added when self._Percent() used it in
                                 // function signature
using syntax_asdl::proc_sig;
using syntax_asdl::suffix_op;
using syntax_asdl::word;
using syntax_asdl::word_part;

using types_asdl::lex_mode_e;

using value_asdl::sh_lvalue;  // for builtin_assign.py and builtin_misc.py
using value_asdl::value;

// Added for osh_parse

// TODO: we need to export headers somehow?
// core/vm.py imports many types

namespace cmd_eval {
  class CommandEvaluator;
};

namespace expr_eval {
  class ExprEvaluator;
};

namespace sh_expr_eval {
  class EnvConfig;
};

namespace sh_expr_eval {
  class ArithEvaluator;
  class BoolEvaluator;
  class UnsafeArith;
};

namespace word_eval {
  class NormalWordEvaluator;
};
