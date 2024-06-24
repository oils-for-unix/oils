#include "mycpp/hash.h"

#include "mycpp/gc_str.h"
#include "mycpp/gc_tuple.h"

unsigned fnv1(const char* data, int len) {
  // FNV-1 from http://www.isthe.com/chongo/tech/comp/fnv/#FNV-1
  unsigned h = 2166136261;     // 32-bit FNV-1 offset basis
  constexpr int p = 16777619;  // 32-bit FNV-1 prime
  for (int i = 0; i < len; i++) {
    h *= p;
    // log("1. h = %d", h);
    h ^= data[i];
    // log("2. h = %d", h);
  }
  return h;
}

unsigned hash_key(BigStr* s) {
  return s->hash(fnv1);
}

unsigned hash_key(int n) {
  return fnv1(reinterpret_cast<const char*>(&n), sizeof(n));
}

unsigned hash_key(mops::BigInt n) {
  // Bug fix: our dict sizing is a power of 2, and we don't want integers in
  // the workload to interact badly with it.
  return fnv1(reinterpret_cast<const char*>(&n), sizeof(n));
}

unsigned hash_key(void* p) {
  // e.g. for Dict<Token*, int>, hash the pointer itself, which means we use
  // object IDENTITY, not value.
  return fnv1(reinterpret_cast<const char*>(&p), sizeof(void*));
}

unsigned hash_key(Tuple2<int, int>* t1) {
  return t1->at0() + t1->at1();
}

unsigned hash_key(Tuple2<BigStr*, int>* t1) {
  return t1->at0()->hash(fnv1) + t1->at1();
}
