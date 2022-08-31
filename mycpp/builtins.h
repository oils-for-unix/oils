// builtins.h: Statically typed Python builtins.
//
// Builtin types: tuples, NotImplementedError, AssertionError
// Builtin functions: print(), repr(), ord()
// Builtin operators: str_concat(), str_repeat(), list_repeat()

#ifndef GC_BUILTINS_H
#define GC_BUILTINS_H

class Str;
Str* AllocStr(int len);

void print(Str* s);

void println_stderr(Str* s);

Str* repr(Str* s);

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


// mycpp doesn't understand dynamic format strings yet
inline Str* dynamic_fmt_dummy() {
  Str *Result = AllocStr(1);
  return Result;
}

#endif  // GC_BUILTINS_H
