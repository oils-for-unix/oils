#ifndef ERROR_TYPES_H
#define ERROR_TYPES_H

#ifdef LEAKY_BINDINGS
class Str;
#else
using gc_heap::Str;
#endif

class IndexError {};
class ValueError {};
class KeyError {};

class EOFError {};

class NotImplementedError {
 public:
  NotImplementedError() {
  }
  explicit NotImplementedError(int i) {  // e.g. in expr_to_ast
  }
  explicit NotImplementedError(const char* s) {
  }
  explicit NotImplementedError(Str* s) {
  }
};

class AssertionError {
 public:
  AssertionError() {
  }
  explicit AssertionError(int i) {  // e.g. in expr_to_ast
  }
  explicit AssertionError(const char* s) {
  }
  explicit AssertionError(Str* s) {
  }
};

#endif
