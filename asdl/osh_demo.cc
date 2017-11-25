#include <string>
#include <stdio.h>
#include <stdlib.h>

#include "id_kind.h"
#include "osh.asdl.h"

// Returns the root ref, or -1 for invalid
int GetRootRef(uint8_t* image) {
  if (image[0] != 'O') return -1;
  if (image[1] != 'H') return -1;
  if (image[2] != 'P') return -1;
  if (image[3] != 4) return -1;

  return image[4] + (image[5] << 8) + (image[6] << 16) + (image[7] << 24);
}

int main(int argc, char **argv) {
  if (argc == 0) {
    printf("Expected filename\n");
    return 1;
  }
  FILE *f = fopen(argv[1], "rb");
  if (!f) {
    fprintf(stderr, "Error opening %s\n", argv[1]);
    return 1;
  }
  fseek(f, 0, SEEK_END);
  size_t num_bytes = ftell(f);
  fseek(f, 0, SEEK_SET);  //same as rewind(f);

  uint8_t* image = static_cast<uint8_t*>(malloc(num_bytes + 1));
  fread(image, num_bytes, 1, f);
  fclose(f);

  image[num_bytes] = 0;
  printf("Read %zu bytes\n", num_bytes);

  int root_ref = GetRootRef(image);
  if (root_ref == -1) {
    printf("Invalid image\n");
    return 1;
  }
  // Hm we could make the root ref be a BYTE offset?
  int alignment = 4;
  printf("alignment: %d root: %d\n", alignment, root_ref);

  auto base = reinterpret_cast<uint32_t*>(image);

  size_t offset = alignment * root_ref;
  auto expr = reinterpret_cast<arith_expr_t*>(image + offset);
  //PrintExpr(base, *expr, 0);
}
