// gc_builtins.h: Statically typed Python builtins.
//
// Builtin types: tuples, NotImplementedError, AssertionError
// Builtin functions: print(), repr(), ord()
// Builtin operators: str_concat(), str_repeat(), list_repeat()

#ifndef GC_BUILTINS_H
#define GC_BUILTINS_H

#include "mycpp/common.h"
#include "mycpp/gc_obj.h"

class Str;

class _ExceptionOpaque {
 public:
  _ExceptionOpaque()
      : GC_CLASS_FIXED(header_, kZeroMask, sizeof(_ExceptionOpaque)) {
  }
  GC_OBJ(header_);
};

// mycpp removes constructor arguments
class Exception : public _ExceptionOpaque {};

class IndexError : public _ExceptionOpaque {};

class KeyError : public _ExceptionOpaque {};

class EOFError : public _ExceptionOpaque {};

class KeyboardInterrupt : public _ExceptionOpaque {};

class StopIteration : public _ExceptionOpaque {};

class ValueError {
 public:
  ValueError()
      : GC_CLASS_FIXED(header_, field_mask(), sizeof(ValueError)),
        message(nullptr) {
  }
  explicit ValueError(Str* message)
      : GC_CLASS_FIXED(header_, field_mask(), sizeof(ValueError)),
        message(message) {
  }

  GC_OBJ(header_);
  Str* message;

  static constexpr uint16_t field_mask() {
    return maskbit(offsetof(ValueError, message));
  }
};

// Note these translations by mycpp:
// - AssertionError      -> assert(0);
// - NotImplementedError -> FAIL(kNotImplemented);

// libc::regex_match and other bindings raise RuntimeError
class RuntimeError {
 public:
  explicit RuntimeError(Str* message)
      : GC_CLASS_FIXED(header_, field_mask(), sizeof(RuntimeError)),
        message(message) {
  }

  GC_OBJ(header_);
  Str* message;

  static constexpr uint16_t field_mask() {
    return maskbit(offsetof(RuntimeError, message));
  }
};

// libc::wcswidth raises UnicodeError on invalid UTF-8
class UnicodeError : public RuntimeError {
 public:
  explicit UnicodeError(Str* message) : RuntimeError(message) {
  }
};

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

Str* str(int i);

// Helper function: returns whether the string is a valid integer, and
// populates the result.  (Also used by marksweep_heap.cc; could be moved
// there)
bool StringToInteger(const char* s, int len, int base, int* result);

// String to integer, raising ValueError if invalid
int to_int(Str* s);
int to_int(Str* s, int base);

Str* chr(int i);
int ord(Str* s);

inline int to_int(bool b) {
  return b;
}

bool to_bool(Str* s);

// Used for floating point flags like read -t 0.1
double to_float(Str* s);

inline bool to_bool(int i) {
  return i != 0;
}

bool str_contains(Str* haystack, Str* needle);

// Only used by unit tests
bool str_equals0(const char* c_string, Str* s);

Str* str_concat(Str* a, Str* b);           // a + b when a and b are strings
Str* str_concat3(Str* a, Str* b, Str* c);  // for os_path::join()
Str* str_repeat(Str* s, int times);        // e.g. ' ' * 3

extern Str* kEmptyString;

int hash(Str* s);

int max(int a, int b);

#endif  // GC_BUILTINS_H
