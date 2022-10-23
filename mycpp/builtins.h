// builtins.h: Statically typed Python builtins.
//
// Builtin types: tuples, NotImplementedError, AssertionError
// Builtin functions: print(), repr(), ord()
// Builtin operators: str_concat(), str_repeat(), list_repeat()

#ifndef GC_BUILTINS_H
#define GC_BUILTINS_H

class Str;

class _ExceptionWithoutFields : public Obj {
 public:
  _ExceptionWithoutFields() : Obj(Tag::Opaque, kZeroMask, kNoObjLen) {
  }
};

class IndexError : public _ExceptionWithoutFields {};

class ValueError : public _ExceptionWithoutFields {};

class KeyError : public _ExceptionWithoutFields {};

class EOFError : public _ExceptionWithoutFields {};

class KeyboardInterrupt : public _ExceptionWithoutFields {};

// TODO: should we eliminate args to NotImplementedError and AssertionError?

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
  explicit RuntimeError(Str* message) : message(message) {
  }
  Str* message;
};

// TODO: remove this.  cmd_eval.py RunOilProc uses it, which we probably
// don't need
class TypeError {
 public:
  explicit TypeError(Str* arg) {
    assert(0);
  }
};

void print(Str* s);

void println_stderr(Str* s);

Str* repr(Str* s);

// For hnode::External in asdl/format.py.  TODO: Remove this when that is
// removed.
inline Str* repr(void* obj) {
  InvalidCodePath();
}

inline Str* str(double f) {
  NotImplemented();
}

Str* str(int i);

bool _str_to_int(Str* s, int* result, int base);  // for testing only
int to_int(Str* s);
int to_int(Str* s, int base);

Str* chr(int i);
int ord(Str* s);

inline int to_int(bool b) {
  return b;
}

bool to_bool(Str* s);
double to_float(Str* s);

inline bool to_bool(int i) {
  return i != 0;
}

bool str_contains(Str* haystack, Str* needle);

extern Str* kEmptyString;

// Function that mycpp generates for non-constant format strings
// TODO: switch back to a printf interpreter
inline Str* dynamic_fmt_dummy() {
  return kEmptyString;
}

#endif  // GC_BUILTINS_H
