#ifndef MYLIB_TYPES_H
#define MYLIB_TYPES_H

template <class K, class V>
class Dict;


// NOTE(Jesse): The python that translates to osh_eval.cc relies on these
// functions being inside this namespace, so we have to live with these.

#include "mycpp/leaky_mylib.h"

template <typename K, typename V>
void dict_remove(Dict<K, V>* haystack, K needle);

namespace mylib {

template <typename K, typename V>
void dict_remove(Dict<K, V>* haystack, K needle)
{
  ::dict_remove(haystack, needle);
}


// Used by generated _build/cpp/osh_eval.cc
inline Str* StrFromC(const char* s) {
  return ::StrFromC(s);
}

Tuple2<Str*, Str*> split_once(Str* s, Str* delim);

}  // namespace mylib

//
// Formatter for Python's %s
//

extern mylib::BufWriter gBuf;

#endif  // MYLIB_TYPES_H
