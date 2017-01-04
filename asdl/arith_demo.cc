#include <string>
#include <stdio.h>
#include <stdlib.h>

#include "arith.asdl.h"

void PrintExpr(const uint32_t* base, const arith_expr_t& e, int indent) {
  for (int i = 0; i < indent; ++i) {
    putchar('\t');
  }
  printf("t%hhu ", e.tag());

  switch (e.tag()) {
  case arith_expr_e::Const: {
    auto& e2 = static_cast<const Const&>(e);
    printf("CONST %d\n", e2.i());
    break;
  }
  case arith_expr_e::ArithVar: {
    auto& e2 = static_cast<const ArithVar&>(e);
    printf("VAR %s\n", e2.name(base));
    break;
  }
  case arith_expr_e::ArithUnary: {
    auto& e2 = static_cast<const ArithUnary&>(e);
    printf("UNARY\n");
    break;
  }
  case arith_expr_e::ArithBinary: {
    auto& e2 = static_cast<const ArithBinary&>(e);
    printf("BINARY\n");
    for (int i = 0; i < indent+1; ++i) {
      putchar('\t');
    }
    // TODO: 
    // char* DebugString(op_id_e op_id)
    //printf("INT %d\n", e2.Int(1));
    printf("%hhu\n", e2.op_id());

    PrintExpr(base, e2.left(base), indent+1);
    PrintExpr(base, e2.right(base), indent+1);
    break;
  }
  case arith_expr_e::FuncCall: {
    auto& e2 = static_cast<const FuncCall&>(e);
    printf("FUNC CALL\n");
    for (int i = 0; i < indent+1; ++i) {
      putchar('\t');
    }
    printf("name %s\n", e2.name(base));
    for (int i = 0; i < e2.args_size(base); ++i) {
      PrintExpr(base, e2.args(base, i), indent+1);
    }
    break;
  }
  case arith_expr_e::Index: {
    auto& e2 = static_cast<const Index&>(e);
    printf("INDEX\n");
    PrintExpr(base, e2.a(base), indent+1);
    PrintExpr(base, e2.index(base), indent+1);
    break;
  }
  case arith_expr_e::Slice: {
    auto& e2 = static_cast<const Slice&>(e);
    printf("SLICE\n");
    const arith_expr_t* begin = e2.begin(base);
    const arith_expr_t* end = e2.end(base);
    const arith_expr_t* stride = e2.stride(base);
    PrintExpr(base, e2.a(base), indent+1);
    if (begin) PrintExpr(base, *begin, indent+1);
    if (end) PrintExpr(base, *end, indent+1);
    if (stride) {
      PrintExpr(base, *stride, indent+1);
    } else {
      for (int i = 0; i < indent+1; ++i) {
        putchar('\t');
      }
      printf("stride: %p\n", stride);
    }
    break;
  }
  default:
    printf("OTHER\n");
    break;
  }
}

// Returns the root ref, or -1 for invalid
int GetRootRef(uint8_t* image) {
  if (image[0] != 'O') return -1;
  if (image[1] != 'H') return -1;
  if (image[2] != 'P') return -1;
  if (image[3] != 1) return -1;  // version 1
  if (image[4] != 4) return -1;  // alignment 4

  return image[5] + (image[6] << 8) + (image[7] << 16);
}

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

  size_t offset = alignment * root_ref + 0;
  auto expr = reinterpret_cast<arith_expr_t*>(image + offset);
  PrintExpr(base, *expr, 0);
}
