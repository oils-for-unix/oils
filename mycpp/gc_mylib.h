// gc_mylib.h

#ifndef GC_MYLIB_H
#define GC_MYLIB_H

#include "mycpp/builtins.h"  // Tuple2

namespace mylib {

Tuple2<Str*, Str*> split_once(Str* s, Str* delim);

template <typename K, typename V>
void dict_remove(Dict<K, V>* haystack, K needle);

}

// Global formatter
extern mylib::BufWriter gBuf;

#endif  // GC_MYLIB_H
