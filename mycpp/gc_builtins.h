// gc_builtins.h: Statically typed Python builtins.
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

template <typename K, typename V>
inline bool dict_contains(Dict<K, V>* haystack, K needle) {
  return haystack->position_of_key(needle) != -1;
}

// TODO:
// - Look at entry_ to see if an item is deleted (or is a tombstone once we
// have hash chaining)

template <class K, class V>
class DictIter {
 public:
  explicit DictIter(Dict<K, V>* D) : D_(D), pos_(ValidPosAfter(0)) {
  }
  void Next() {
    pos_ = ValidPosAfter(pos_ + 1);
  }
  bool Done() {
    return pos_ == -1;
  }
  K Key() {
    return D_->keys_->items_[pos_];
  }
  V Value() {
    return D_->values_->items_[pos_];
  }

 private:
  int ValidPosAfter(int pos) {
    // Returns the position of a valid entry at or after index i_.  Or -1 if
    // there isn't one.  Advances i_ too.
    while (true) {
      if (pos >= D_->capacity_) {
        return -1;
      }
      int index = D_->entry_->items_[pos];
      if (index == kDeletedEntry) {
        ++pos;
        continue;  // increment again
      }
      if (index == kEmptyEntry) {
        return -1;
      }
      break;
    }
    return pos;
  }

  Dict<K, V>* D_;
  int pos_;
};

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
