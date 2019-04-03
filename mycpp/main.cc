// _main.cc: wrapper for all the examples

#include <stdlib.h>

void run_tests();
void run_benchmarks();

int main(int argc, char **argv) {
  if (getenv("BENCHMARK")) {
    run_benchmarks();
  } else {
    run_tests();
  }
}
