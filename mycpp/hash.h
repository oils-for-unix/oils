#ifndef MYCPP_HASH_H
#define MYCPP_HASH_H

typedef unsigned (*HashFunc)(const char*, int);

unsigned fnv1(const char* data, int len);

template <typename L, typename R>
class Tuple2;

class BigStr;

unsigned hash_key(BigStr* s);
unsigned hash_key(int n);
unsigned hash_key(Tuple2<int, int>* t1);
unsigned hash_key(Tuple2<BigStr*, int>* t1);
unsigned hash_key(void* p);  // e.g. for Dict<Token*, int>

#endif  // MYCPP_HASH_H
