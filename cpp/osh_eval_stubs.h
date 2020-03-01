// osh_eval_stubs.h

#ifndef OSH_EVAL_STUBS_H
#define OSH_EVAL_STUBS_H

// Hacky stubs

namespace expr_eval {
  class OilEvaluator;
}

// problem: incomplete type
namespace prompt {
  class Evaluator;
}

// problem: incomplete type
namespace cmd_exec {
  class Executor;
}

namespace util {
  Str* BackslashEscape(Str* a, Str* b);
}

// TODO: Should these have their own file?
namespace pyutil {
  Str* strerror_IO(IOError* e);
  Str* strerror_OS(OSError* e);
}


#endif  // OSH_EVAL_STUBS_H

