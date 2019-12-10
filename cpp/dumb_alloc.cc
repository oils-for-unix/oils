// dumb_alloc.cc: Test this C++ mechanism as a lower bound on performance.

#include "dumb_alloc.h"

#include <stdio.h>

// 100 MiB of memory
char kMem[100 << 20];

int gMemPos;
int gNumNew = 0;
int gNumDelete = 0;

// This global interface is silly ...

void* operator new(size_t size) {
  char* p = &(kMem[gMemPos]);
  fprintf(stderr, "\tnew(%d) = %p\n", size, p);
  gMemPos += size;
  ++gNumNew;
  return p;
}

void operator delete(void* p) {
  fprintf(stderr, "\tdelete %p\n", p);
  ++gNumDelete;
}

namespace dumb_alloc {

void Summarize() {
  fprintf(stderr, "gNumNew = %d\n", gNumNew);
  fprintf(stderr, "gNumDelete = %d\n", gNumDelete);
}

};
