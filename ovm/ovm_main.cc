#include <string>
#include <stdio.h>
#include <stdlib.h>

#include "opcode.h"

int main(int argc, char **argv) {
  if (argc == 0) {
    printf("Expected filename\n");
    return 1;
  }
  FILE *f = fopen(argv[1], "rb");
  if (!f) {
    printf("Error opening %s", argv[1]);
    return 1;
  }
  fseek(f, 0, SEEK_END);
  size_t num_bytes = ftell(f);
  fseek(f, 0, SEEK_SET);  //same as rewind(f);

  uint8_t* bytecode = static_cast<uint8_t*>(malloc(num_bytes));
  fread(bytecode, num_bytes, 1, f);
  fclose(f);

  printf("Read %zu bytes\n", num_bytes);

  int i = 0;
  int extended_arg = 0;

  int n = 0;

  while (i < num_bytes) {
    uint8_t op = bytecode[i];
    i++;
    printf("%s\n", kOpcodeNames[op]);

    if (op > HAVE_ARGUMENT) {
      int oparg = bytecode[i] + bytecode[i+1]*256 + extended_arg;
      printf("  arg %d\n", oparg);
      i += 2;
    }
    n++;
  }

  printf("Read %d instructions\n", n);
}
