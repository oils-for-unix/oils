#ifndef ERROR_TYPES_H
#define ERROR_TYPES_H

class Str;

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

// Python's RuntimeError looks like this.  . libc::regex_match and other
// bindings raise it.
class RuntimeError {
 public:
  RuntimeError(Str* message) : message(message) {
  }
  Str* message;
};

#endif  // ERROR_TYPES_H
