// osh_eval_stubs.h

#ifndef OSH_EVAL_STUBS_H
#define OSH_EVAL_STUBS_H

// Hacky stubs

#include "id_kind_asdl.h"
#include "runtime_asdl.h"
#include "syntax_asdl.h"

namespace vm {
class _Executor;
}
namespace word_eval {
class AbstractWordEvaluator;
}

namespace expr_eval {
class OilEvaluator {
 public:
  // TODO: Should return value_t
  void* EvalExpr(syntax_asdl::expr_t* node) {
    assert(0);
  }
  void CheckCircularDeps() {
    assert(0);
  }
  vm::_Executor* shell_ex;
  word_eval::AbstractWordEvaluator* word_ev;
};
}  // namespace expr_eval

namespace builtin_process {
class _TrapHandler {
 public:
  syntax_asdl::command_t* node;
};
}  // namespace builtin_process

namespace executor {
class ShellExecutor {
 public:
  // overload
  int RunSimpleCommand(runtime_asdl::cmd_value__Argv* cmd_val, bool do_fork) {
    assert(0);
  }
  int RunSimpleCommand(runtime_asdl::cmd_value__Argv* cmd_val, bool do_fork,
                       bool call_procs) {
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
}  // namespace executor

#endif  // OSH_EVAL_STUBS_H
