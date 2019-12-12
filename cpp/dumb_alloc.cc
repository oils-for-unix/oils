// dumb_alloc.cc: Test this C++ mechanism as a lower bound on performance.

#include "dumb_alloc.h"

#include <stdio.h>

// 100 MiB of memory
char kMem[100 << 20];

int gMemPos = 0;
int gNumNew = 0;
int gNumDelete = 0;

// This global interface is silly ...

void* operator new(size_t size) {
  char* p = &(kMem[gMemPos]);
  //fprintf(stderr, "\tnew(%d) = %p\n", size, p);
  //printf("__ %d\n", size);
  gMemPos += size;
  ++gNumNew;
  return p;
}

// noexcept fixes Clang warning
void operator delete(void* p) noexcept {
  //fprintf(stderr, "\tdelete %p\n", p);
  ++gNumDelete;
}

char kMem2[100 << 20];
int gMemPos2 = 0;
int gNumMalloc = 0;
int gNumFree = 0;

void* dumb_malloc(size_t size) noexcept {
  char* p = &(kMem2[gMemPos2]);
  //fprintf(stderr, "malloc %d\n", size);
  gMemPos2 += size;
  ++gNumMalloc;
  return p;
}

void dumb_free(void* p) noexcept {
  //fprintf(stderr, "free\n");
  ++gNumFree;
}

namespace dumb_alloc {

void Summarize() {
  fprintf(stderr, "\n");
  fprintf(stderr, "dumb_alloc:\n");
  fprintf(stderr, "\tgNumNew = %d\n", gNumNew);
  fprintf(stderr, "\tgNumDelete = %d\n", gNumDelete);
  fprintf(stderr, "\tgMemPos = %d\n", gMemPos);
  fprintf(stderr, "\n");
  fprintf(stderr, "\tgNumMalloc = %d\n", gNumMalloc);
  fprintf(stderr, "\tgNumFree = %d\n", gNumFree);
  fprintf(stderr, "\tgMemPos2 = %d\n", gMemPos2);
}

};
