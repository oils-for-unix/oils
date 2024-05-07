#include <sys/sdt.h>

int main(void) {
  DTRACE_PROBE(test, main);
  return 0;
}
