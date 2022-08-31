#ifndef GC_MYLIB_H
#define GC_MYLIB_H

#include "mycpp/builtins.h"
#include "mycpp/leaky_mylib.h"

namespace mylib {

Tuple2<Str*, Str*> split_once(Str* s, Str* delim);

template <typename K, typename V>
void dict_remove(Dict<K, V>* haystack, K needle);

}  // namespace mylib

// Global formatter
extern mylib::BufWriter gBuf;

#endif  // GC_MYLIB_H
