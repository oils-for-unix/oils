#ifndef OLDSTL_BINDINGS
  #error "This file contains definitions for OLDSTL builtins."
#endif

#include "mycpp/gc_builtins.h"

class Str;

#if 0
void print(Str* s);

// log() generates code that writes this
void println_stderr(Str* s);

// Display a quoted representation of a string.  word_.Pretty() uses it.
Str* repr(Str* s);

bool _str_to_int(Str* s, int* result, int base);  // for testing only
int to_int(Str* s);
int to_int(Str* s, int base);

// int(a == b) used in arithmetic evaluator
inline int to_int(bool b) {
  return b;
}

inline bool to_bool(int i) {
  return i != 0;
}
#endif

inline bool to_bool(Str* s) {
  return len(s) != 0;
}

inline double to_float(Str* s) {
  double result = atof(s->data_);
  return result;
}

inline Str* chr(int i) {
  char* buf = static_cast<char*>(malloc(2));
  buf[0] = i;
  buf[1] = '\0';
  return CopyBufferIntoNewStr(buf, 1);
}

inline int ord(Str* s) {
  assert(len(s) == 1);
  // signed to unsigned conversion, so we don't get values like -127
  uint8_t c = static_cast<uint8_t>(s->data_[0]);
  return c;
}

inline Str* str(int i) {
  char* buf = static_cast<char*>(malloc(kIntBufSize));
  int len = snprintf(buf, kIntBufSize, "%d", i);
  return CopyBufferIntoNewStr(buf, len);
}

inline Str* str(double f) {  // TODO: should be double
  NotImplemented();          // Uncalled
}

// mycpp doesn't understand dynamic format strings yet
inline Str* dynamic_fmt_dummy() {
  /* NotImplemented(); */
  return StrFromC("dynamic_fmt_dummy");
}
