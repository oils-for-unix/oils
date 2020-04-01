// osh_eval_stubs.h

#ifndef OSH_EVAL_STUBS_H
#define OSH_EVAL_STUBS_H

// Hacky stubs

#include "id_kind_asdl.h"
#include "runtime_asdl.h"
#include "syntax_asdl.h"

namespace expr_eval {
  class OilEvaluator;
}

// problem: incomplete type
namespace prompt {
  class Evaluator {
   public:
    Str* EvalPrompt(runtime_asdl::value_t* val) {
      assert(0);
    }
  };
}

// problem: incomplete type
#if 0
namespace cmd_exec {
  class Executor {
   public:
    Str* RunCommandSub(syntax_asdl::command_t* node) {
      assert(0);
    }
    Str* RunProcessSub(syntax_asdl::command_t* node, Id_t id) {
      assert(0);
    }
  };
}
#endif

namespace util {
  inline Str* BackslashEscape(Str* a, Str* b) {
    assert(0);
  }
  class UserExit {
   public:
     UserExit(int arg) {
     }
  };
}

// TODO: Should these have their own file?
namespace pyutil {
  inline Str* strerror_IO(IOError* e) {
    assert(0);
  }
  inline Str* strerror_OS(OSError* e) {
    assert(0);
  }
}

//
// Stubs added for osh/cmd_exec.py
//

namespace builtin_misc {
  class _Builtin {
   public:
    int Run(runtime_asdl::cmd_value_t* cmd_val) {
      assert(0);
    }
  };
}

namespace builtin_process {
  class _TrapHandler;
}

namespace util {
  class DebugFile;
}

namespace executor {
  class ShellExecutor {
   public:
     // overload
     int RunSimpleCommand(runtime_asdl::cmd_value__Argv* cmd_val,
                          bool do_fork) {
       assert(0);
     }
     int RunSimpleCommand(runtime_asdl::cmd_value__Argv* cmd_val,
                          bool do_fork, bool call_procs) {
       assert(0);
     }
     int RunBackgroundJob(syntax_asdl::command_t* node) {
       assert(0);
     }
     int RunPipeline(syntax_asdl::command__Pipeline* node) {
       assert(0);
     }
     int RunSubshell(syntax_asdl::command__Subshell* node) {
       assert(0);
     }
     bool PushRedirects(List<runtime_asdl::redirect*>* redirects) {
       assert(0);
     }
     void PopRedirects() {
       assert(0);
     }
     Str* RunCommandSub(syntax_asdl::command_t* node) {
       assert(0);
     }
     Str* RunProcessSub(syntax_asdl::command_t* node, Id_t op_id) {
       assert(0);
     }
  };
}

#endif  // OSH_EVAL_STUBS_H

