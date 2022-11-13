// cpp/translation_stubs.h

#ifndef CPP_TRANSLATION_STUBS_H
#define CPP_TRANSLATION_STUBS_H

// Hm is this overload really necessary?
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

#endif  // CPP_TRANSLATION_STUBS_H
