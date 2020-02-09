// dumb_alloc.cc: Test this C++ mechanism as a lower bound on performance.

#include "dumb_alloc.h"

#include <stdio.h>

// 200 MiB of memory
char kMem[200 << 20];

int gMemPos = 0;
int gNumNew = 0;
int gNumDelete = 0;

// Align returned pointers to the worst case of 8 bytes (64-bit pointers)
inline size_t aligned(size_t n) {
  // https://stackoverflow.com/questions/2022179/c-quick-calculation-of-next-multiple-of-4
  return (n + 7) & ~7;
  // return (n + 15) & ~15;
}

  // This global interface is silly ...

#ifdef DUMB_ALLOC
void* operator new(size_t size) {
  char* p = &(kMem[gMemPos]);
#ifdef SIZE_LOG
  printf("new %zu\n", size);
#endif
  gMemPos += aligned(size);
  ++gNumNew;
  return p;
}

// noexcept fixes Clang warning
void operator delete(void* p) noexcept {
  // fprintf(stderr, "\tdelete %p\n", p);
  ++gNumDelete;
}
#endif

char kMem2[200 << 20];
int gMemPos2 = 0;
int gNumMalloc = 0;
int gNumFree = 0;

#ifdef DUMB_ALLOC
void* dumb_malloc(size_t size) noexcept {
  char* p = &(kMem2[gMemPos2]);
#ifdef SIZE_LOG
  printf("malloc %zu\n", size);
#endif
  gMemPos2 += aligned(size);
  ++gNumMalloc;
  return p;
}

void dumb_free(void* p) noexcept {
  // fprintf(stderr, "free\n");
  ++gNumFree;
}
#endif

namespace dumb_alloc {

void Summarize() {
#ifdef DUMB_ALLOC
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

}  // namespace dumb_alloc
