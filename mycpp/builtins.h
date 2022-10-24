// builtins.h: Statically typed Python builtins.
//
// Builtin types: tuples, NotImplementedError, AssertionError
// Builtin functions: print(), repr(), ord()
// Builtin operators: str_concat(), str_repeat(), list_repeat()

#ifndef GC_BUILTINS_H
#define GC_BUILTINS_H

class Str;

class _ExceptionOpaque : public Obj {
 public:
  _ExceptionOpaque() : Obj(Tag::Opaque, kZeroMask, kNoObjLen) {
  }
};

// mycpp removes constructor arguments
class AssertionError : public _ExceptionOpaque {};

class IndexError : public _ExceptionOpaque {};

class ValueError : public _ExceptionOpaque {};

class KeyError : public _ExceptionOpaque {};

class EOFError : public _ExceptionOpaque {};

class KeyboardInterrupt : public _ExceptionOpaque {};

// TODO: we could eliminate args to NotImplementedError, like we do for
// AssertionError
class NotImplementedError : public _ExceptionOpaque {
 public:
  NotImplementedError() : _ExceptionOpaque() {
  }
  // used in expr_to_ast
  explicit NotImplementedError(int i) : _ExceptionOpaque() {
  }
  // called with Id_str()
  explicit NotImplementedError(const char* s) : _ExceptionOpaque() {
  }
  explicit NotImplementedError(Str* s) : _ExceptionOpaque() {
  }
};

// libc::regex_match and other bindings raise RuntimeError
class RuntimeError : public Obj {
 public:
  explicit RuntimeError(Str* message);
  Str* message;
};

constexpr uint16_t maskof_RuntimeError() {
  return maskbit(offsetof(RuntimeError, message));
}

inline RuntimeError::RuntimeError(Str* message)
    : Obj(Tag::FixedSize, maskof_RuntimeError(), kNoObjLen), message(message) {
}

// Python 2 has a dubious distinction between IOError and OSError, so mycpp
// generates this base class to catch both.
class IOError_OSError : public _ExceptionOpaque {
 public:
  explicit IOError_OSError(int err_num) : _ExceptionOpaque(), errno_(err_num) {
  }
  int errno_;
};

class IOError : public IOError_OSError {
 public:
  explicit IOError(int err_num) : IOError_OSError(err_num) {
  }
};

class OSError : public IOError_OSError {
 public:
  explicit OSError(int err_num) : IOError_OSError(err_num) {
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

// Helper function: returns whether the string is a valid integer, and
// populates the result.  (Also used by marksweep_heap.cc; could be moved
// there)
bool StringToInteger(char* s, int len, int base, int* result);

// String to integer, raising ValueError if invalid
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
