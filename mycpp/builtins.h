// builtins.h: Statically typed Python builtins.
//
// Builtin types: tuples, NotImplementedError, AssertionError
// Builtin functions: print(), repr(), ord()
// Builtin operators: str_concat(), str_repeat(), list_repeat()

#ifndef GC_BUILTINS_H
#define GC_BUILTINS_H

#include "mycpp/common.h"

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


#ifndef OLDSTL_BINDINGS

  #include <algorithm>  // min(), sort()
  #include <climits>    // CHAR_BIT

  #include "mycpp/error_types.h"
  #include "mycpp/gc_containers.h"
  #include "mycpp/leaky_mylib.h"  // TODO: remove inverted dependency
  #include "mycpp/tuple_types.h"
  #include "mycpp/gc_list_iter.h"
  #include "mycpp/dict_iter.h"

template <typename K, typename V>
inline bool dict_contains(Dict<K, V>* haystack, K needle) {
  return haystack->position_of_key(needle) != -1;
}

// TODO:
// - Look at entry_ to see if an item is deleted (or is a tombstone once we
// have hash chaining)

#endif  // OLDSTL_BINDINGS

// list(L) copies the list
template <typename T>
List<T>* list(List<T>* other) {
  auto result = NewList<T>();
  for (int i = 0; i < len(other); ++i) {
    result->set(i, other->index_(i));
  }
  return result;
}

#endif  // GC_BUILTINS_H
