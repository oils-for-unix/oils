#ifndef MYLIB_TYPES_H
#define MYLIB_TYPES_H

// NOTE(Jesse): The python that translates to osh_eval.cc relies on these
// functions being inside this namespace, so we have to live with these.

#include "mycpp/leaky_mylib.h"

namespace mylib {

// Used by generated _build/cpp/osh_eval.cc
inline Str* StrFromC(const char* s) {
  return ::StrFromC(s);
}

template <typename V>
inline void dict_remove(Dict<Str*, V>* haystack, Str* needle) {
  int pos = find_by_key(haystack->items_, needle);
  if (pos == -1) {
    return;
  }
  haystack->items_[pos].first = nullptr;
}

// TODO: how to do the int version of this?  Do you need an extra bit?
template <typename V>
inline void dict_remove(Dict<int, V>* haystack, int needle) {
  NotImplemented();
}

Tuple2<Str*, Str*> split_once(Str* s, Str* delim);

}  // namespace mylib

//
// Formatter for Python's %s
//

extern mylib::BufWriter gBuf;

#endif  // MYLIB_TYPES_H
