#ifndef MYCPP_HASH_H
#define MYCPP_HASH_H

typedef int (*HashFunc)(const char*, int);

int fnv1(const char* data, int len);

template <typename L, typename R>
class Tuple2;

class Str;

int hash_key(Str* s);
int hash_key(int n);
int hash_key(Tuple2<int, int>* t1);
int hash_key(Tuple2<Str*, int>* t1);

#endif  // MYCPP_HASH_H
