/* Based on example.c from SWIG docs */

#include <stdio.h>

#include "example.h"

namespace fanos {

int fact(int n) {
    if (n < 0){ /* This should probably return an error, but this is simpler */
        return 0;
    }
    if (n == 0) {
        return 1;
    }
    else {
        /* testing for overflow would be a good idea here */
        return n * fact(n-1);
    }
}

int add(int x, int y) {
  return x + y;
}

void send(int fd, Str* s) {
  printf("hi\n");
}

}
