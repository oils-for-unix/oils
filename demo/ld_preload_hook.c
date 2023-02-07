// Chaining malloc
// https://stackoverflow.com/questions/6083337/overriding-malloc-using-the-ld-preload-mechanism

#define _GNU_SOURCE

#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

#if 0
FILE *fopen(const char *path, const char *mode) {
    printf("Always failing fopen\n");
    return NULL;
}
#endif

#if 1
static void *(*real_malloc)(size_t) = NULL;

static void mtrace_init(void) {
  real_malloc = dlsym(RTLD_NEXT, "malloc");
  if (NULL == real_malloc) {
    fprintf(stderr, "Error in `dlsym`: %s\n", dlerror());
  }
}

void *malloc(size_t size) {
  if (real_malloc == NULL) {
    mtrace_init();
  }

  void *p = NULL;
  fprintf(stderr, "HOOK malloc(%ld) = ", size);
  p = real_malloc(size);
  fprintf(stderr, "%p\n", p);
  return p;
}
#endif
