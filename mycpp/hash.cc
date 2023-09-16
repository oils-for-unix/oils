#include "mycpp/hash.h"

#include "mycpp/gc_str.h"
#include "mycpp/gc_tuple.h"

int fnv1(const char* data, int len) {
  // FNV-1 from http://www.isthe.com/chongo/tech/comp/fnv/#FNV-1
  int h = 2166136261;          // 32-bit FNV-1 offset basis
  constexpr int p = 16777619;  // 32-bit FNV-1 prime
  for (int i = 0; i < len; i++) {
    h *= data[i];
    h ^= p;
  }
  return h;
}

int hash_key(Str* s) {
  return s->hash(fnv1);
}

int hash_key(int n) {
  return n;
}

int hash_key(Tuple2<int, int>* t1) {
  return t1->at0() + t1->at1();
}

int hash_key(Tuple2<Str*, int>* t1) {
  return t1->at0()->hash(fnv1) + t1->at1();
}
