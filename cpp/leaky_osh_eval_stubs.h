// leaky_osh_eval_stubs.h

#ifndef OSH_EVAL_STUBS_H
#define OSH_EVAL_STUBS_H

// Hacky stubs

#include "_gen/core/runtime.asdl.h"
#include "_gen/frontend/id_kind.asdl.h"
#include "_gen/frontend/syntax.asdl.h"

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

namespace signal_def {

const int NO_SIGNAL = -1;

inline List<Tuple2<Str*, int>*>* AllNames() {
  NotImplemented();
}

inline int GetNumber(Str* sig_spec) {
  NotImplemented();
}
}  // namespace signal_def

#endif  // OSH_EVAL_STUBS_H
