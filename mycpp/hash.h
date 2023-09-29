#ifndef MYCPP_HASH_H
#define MYCPP_HASH_H

typedef unsigned (*HashFunc)(const char*, int);

unsigned fnv1(const char* data, int len);

template <typename L, typename R>
class Tuple2;

class Str;

unsigned hash_key(Str* s);
unsigned hash_key(int n);
unsigned hash_key(Tuple2<int, int>* t1);
unsigned hash_key(Tuple2<Str*, int>* t1);

#endif  // MYCPP_HASH_H
