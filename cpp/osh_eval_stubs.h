// osh_eval_stubs.h

#ifndef OSH_EVAL_STUBS_H
#define OSH_EVAL_STUBS_H

// Hacky stubs

#include "id_kind_asdl.h"
#include "runtime_asdl.h"
#include "syntax_asdl.h"

namespace expr_eval {
class OilEvaluator {
 public:
  // TODO: Should return value_t
  void* EvalExpr(syntax_asdl::expr_t* node) {
    assert(0);
  }
};
}  // namespace expr_eval

// problem: incomplete type
namespace prompt {
class Evaluator {
 public:
  Str* EvalPrompt(runtime_asdl::value_t* val) {
    assert(0);
  }
};
}  // namespace prompt

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

// stub for cmd_eval.py
#if 0
namespace args {
class UsageError {
 public:
  Str* msg;
  int span_id;
};
}  // namespace args
#endif

namespace util {

inline Str* BackslashEscape(Str* s, Str* meta_chars) {
  int upper_bound = s->len_ * 2;
  char* buf = static_cast<char*>(malloc(upper_bound));
  char* p = buf;

  for (int i = 0; i < s->len_; ++i) {
    char c = s->data_[i];
    if (memchr(meta_chars->data_, c, meta_chars->len_)) {
      *p++ = '\\';
    }
    *p++ = c;
  }
  int len = p - buf;
  return new Str(buf, len);
}

class UserExit {
 public:
  UserExit(int arg) {
  }
};
}  // namespace util

// TODO: Should these have their own file?
namespace pyutil {
inline Str* strerror_IO(IOError* e) {
  assert(0);
}
inline Str* strerror_OS(OSError* e) {
  assert(0);
}
}  // namespace pyutil

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
}  // namespace builtin_misc

namespace builtin_process {
class _TrapHandler {
 public:
  syntax_asdl::command_t* node;
};
}  // namespace builtin_process

namespace util {
class DebugFile {
 public:
  DebugFile(mylib::Writer* writer) {
  }
};
}  // namespace util

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
