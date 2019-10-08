#include "types_asdl.h"
#include "syntax_asdl.h"
#include "runtime_asdl.h"

#include "mylib.h"

// TODO: Should this just call oil::main(argv) or something?

int main(int argc, char **argv) {
  log("sizeof(int): %d", sizeof(int));
}
