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
  if (image[3] != 1) return -1;  // version 1
  if (image[4] != 4) return -1;  // alignment 4

  return image[5] + (image[6] << 8) + (image[7] << 16);
}

void PrintToken(const uint32_t* base, const token_t& e, int indent) {
  for (int i = 0; i < indent; ++i) {
    putchar('\t');
  }
  printf("Token %hhu %s\n", e.id(), e.val(base));
}

void PrintWordPart(const uint32_t* base, const word_part_t& e, int indent) {
  for (int i = 0; i < indent; ++i) {
    putchar('\t');
  }
  printf("t%hhu ", e.tag());
  switch (e.tag()) {
  case word_part_e::LiteralPart: {
    auto& e2 = static_cast<const LiteralPart&>(e);
    printf("LiteralPart\n");
    PrintToken(base, e2.token(base), indent+1);
    break;
  }
  default:
    printf("OTHER word_part\n");
    break;
  }
}

void PrintWord(const uint32_t* base, const word_t& e, int indent) {
  for (int i = 0; i < indent; ++i) {
    putchar('\t');
  }
  printf("t%hhu ", e.tag());
  switch (e.tag()) {
  case word_e::CompoundWord: {
    auto& e2 = static_cast<const CompoundWord&>(e);
    printf("CompoundWord %d\n", e2.parts_size(base));
    for (int i = 0; i < e2.parts_size(base); ++i) {
      PrintWordPart(base, e2.parts(base, i), indent+1);
    }
    break;
  }
  default:
    printf("OTHER word\n");
    break;
  }
}

void PrintCommand(const uint32_t* base, const command_t& e, int indent) {
  for (int i = 0; i < indent; ++i) {
    putchar('\t');
  }
  printf("t%hhu ", e.tag());

  switch (e.tag()) {
  case command_e::SimpleCommand: {
    auto& e2 = static_cast<const SimpleCommand&>(e);
    printf("SimpleCommand %d\n", e2.words_size(base));
    for (int i = 0; i < e2.words_size(base); ++i) {
      PrintWord(base, e2.words(base, i), indent+1);
    }
    break;
  }
  case command_e::Assignment: {
    auto& e2 = static_cast<const Assignment&>(e);
    printf("Assignment flags: ");
    for (int i = 0; i < e2.flags_size(base); ++i) {
      printf("%s ", e2.flags(base, i));
    }
    printf("\n");
    break;
  }
  case command_e::AndOr: {
    auto& e2 = static_cast<const AndOr&>(e);
    printf("Ops: ");
    for (int i = 0; i < e2.ops_size(base); ++i) {
      printf("%hhu ", e2.ops(base, i));
    }
    printf("\n");
    for (int i = 0; i < e2.children_size(base); ++i) {
      PrintCommand(base, e2.children(base, i), indent+1);
    }
    printf("\n");
    break;
  }
  case command_e::CommandList: {
    auto& e2 = static_cast<const CommandList&>(e);
    printf("CommandList %d\n", e2.children_size(base));
    for (int i = 0; i < e2.children_size(base); ++i) {
      PrintCommand(base, e2.children(base, i), indent+1);
    }
    break;
  }
  default:
    printf("OTHER\n");
    break;
  }
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
  auto expr = reinterpret_cast<command_t*>(image + offset);
  PrintCommand(base, *expr, 0);
}
