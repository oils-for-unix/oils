// gc_mylib.h

#ifndef GC_MYLIB_H
#define GC_MYLIB_H

#include "mycpp/gc_builtins.h"  // Tuple2

namespace mylib {

Tuple2<Str*, Str*> split_once(Str* s, Str* delim);

template <typename V>
void dict_remove(Dict<Str*, V>* haystack, Str* needle) {
  int pos = haystack->position_of_key(needle);
  if (pos == -1) {
    return;
  }
  haystack->entry_->items_[pos] = kDeletedEntry;
  // Zero out for GC.  These could be nullptr or 0
  haystack->keys_->items_[pos] = 0;
  haystack->values_->items_[pos] = 0;
  haystack->len_--;
}

}  // namespace mylib

// Global formatter
extern mylib::BufWriter gBuf;

#endif  // GC_MYLIB_H
