// open() isn't C or C++; it's POSIX

#include <fcntl.h>   // open
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>   // vprintf

// #include "dumb_alloc.h"
// #include "mylib.h"

void log(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vprintf(fmt, args);
  va_end(args);
  printf("\n");
}

int main(int argc, char** argv) {
  log("hello %d", argc);

  if (argc == 2) {
    int fd = ::open(argv[1], 0, 0);
    log("fd = %d", fd);
  } else {
    log("expected filename");
  }
  return 0;
}
