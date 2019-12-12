// dumb_alloc.cc: Test this C++ mechanism as a lower bound on performance.

#include "dumb_alloc.h"

#include <stdio.h>

// 100 MiB of memory
char kMem[100 << 20];

int gMemPos = 0;
int gNumNew = 0;
int gNumDelete = 0;

// https://stackoverflow.com/questions/2022179/c-quick-calculation-of-next-multiple-of-4
inline size_t aligned(size_t n) {
  //return (n + 7) & ~7;
  return (n + 15) & ~15;
}

// This global interface is silly ...

#ifndef TCMALLOC
void* operator new(size_t size) {
  char* p = &(kMem[gMemPos]);
  //fprintf(stderr, "\tnew(%d) = %p\n", size, p);
  //printf("__ %d\n", size);
  gMemPos += aligned(size);
  ++gNumNew;
  return p;
}

// noexcept fixes Clang warning
void operator delete(void* p) noexcept {
  //fprintf(stderr, "\tdelete %p\n", p);
  ++gNumDelete;
}
#endif

char kMem2[100 << 20];
int gMemPos2 = 0;
int gNumMalloc = 0;
int gNumFree = 0;

#ifndef TCMALLOC
void* dumb_malloc(size_t size) noexcept {
  char* p = &(kMem2[gMemPos2]);
  //fprintf(stderr, "malloc %d\n", size);
  gMemPos2 += aligned(size);
  ++gNumMalloc;
  return p;
}

void dumb_free(void* p) noexcept {
  //fprintf(stderr, "free\n");
  ++gNumFree;
}
#endif

namespace dumb_alloc {

void Summarize() {
#ifndef TCMALLOC
  fprintf(stderr, "\n");
  fprintf(stderr, "dumb_alloc:\n");
  fprintf(stderr, "\tgNumNew = %d\n", gNumNew);
  fprintf(stderr, "\tgNumDelete = %d\n", gNumDelete);
  fprintf(stderr, "\tgMemPos = %d\n", gMemPos);
  fprintf(stderr, "\n");
  fprintf(stderr, "\tgNumMalloc = %d\n", gNumMalloc);
  fprintf(stderr, "\tgNumFree = %d\n", gNumFree);
  fprintf(stderr, "\tgMemPos2 = %d\n", gMemPos2);
#endif
}

};
