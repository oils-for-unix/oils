/* File: example.h */

class Str;  // mycpp/runtime

namespace fanos {

int fact(int n);

// Note: SWIG doesn't find inline functions
int add(int x, int y);

void send(int fd, Str* s);

}
