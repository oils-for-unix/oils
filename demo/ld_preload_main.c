#include <stdio.h>
#include <stdlib.h>

int main(void) {
  char* p;
  for (int i = 0; i < 10; ++i) {
    p = malloc(1000);
    printf("p = %p\n", p);
  }

  printf("Calling the fopen() function...\n");

  FILE* fd = fopen("test.txt", "r");
  if (!fd) {
    printf("fopen() returned NULL\n");
    return 1;
  }

  printf("fopen() succeeded\n");

  return 0;
}
