#ifndef MYCPP_COMPARATORS_H
#define MYCPP_COMPARATORS_H

#include <string.h>  // memcmp

#include <algorithm>  // std::min()

#include "mycpp/gc_mops.h"  // mops::BigInt
#include "mycpp/gc_str.h"   // len()

template <typename L, typename R>
class Tuple2;

bool str_equals(BigStr* left, BigStr* right);
bool maybe_str_equals(BigStr* left, BigStr* right);

bool items_equal(BigStr* left, BigStr* right);
bool keys_equal(BigStr* left, BigStr* right);

// No List<T> comparison by pointer
inline bool items_equal(void* left, void* right) {
  assert(0);
}

// e.g. for Dict<Token*, int>, use object IDENTITY, not value
inline bool keys_equal(void* left, void* right) {
  return left == right;
}

inline bool items_equal(int left, int right) {
  return left == right;
}

inline bool keys_equal(int left, int right) {
  return items_equal(left, right);
}

inline bool items_equal(mops::BigInt left, mops::BigInt right) {
  return left == right;
}

inline bool keys_equal(mops::BigInt left, mops::BigInt right) {
  return items_equal(left, right);
}

bool items_equal(Tuple2<int, int>* t1, Tuple2<int, int>* t2);
bool keys_equal(Tuple2<int, int>* t1, Tuple2<int, int>* t2);

bool items_equal(Tuple2<BigStr*, int>* t1, Tuple2<BigStr*, int>* t2);
bool keys_equal(Tuple2<BigStr*, int>* t1, Tuple2<BigStr*, int>* t2);

namespace id_kind_asdl {
enum class Kind;
};

// Defined in cpp/translation_stubs.h
bool items_equal(id_kind_asdl::Kind left, id_kind_asdl::Kind right);

inline int int_cmp(int a, int b) {
  if (a == b) {
    return 0;
  }
  return a < b ? -1 : 1;
}

// mylib::str_cmp is in this common header to avoid gc_list.h -> gc_mylib.h
// dependency
//
// It's also used for _cmp(BigStr*) in gc_list.
namespace mylib {

// Used by [[ a > b ]] and so forth
inline int str_cmp(BigStr* a, BigStr* b) {
  int len_a = len(a);
  int len_b = len(b);

  int min = std::min(len_a, len_b);
  if (min == 0) {
    return int_cmp(len_a, len_b);
  }
  int comp = memcmp(a->data_, b->data_, min);
  if (comp == 0) {
    return int_cmp(len_a, len_b);  // tiebreaker
  }
  return comp;
}

}  // namespace mylib

#endif  // MYCPP_COMPARATORS_H
