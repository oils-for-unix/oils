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

namespace util {
  inline Str* BackslashEscape(Str* a, Str* b) {
    assert(0);
  }
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


#endif  // OSH_EVAL_STUBS_H

