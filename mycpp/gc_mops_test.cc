#include "mycpp/gc_mops.h"

#include "mycpp/runtime.h"
#include "vendor/greatest.h"

TEST bigint_test() {
  // You need to instantiate it as a BigInt, the constant (1) doesn't work
  // And also use %ld

  mops::BigInt i = mops::BigInt{1} << 31;
  log("bad  i = %d", i);  // bug
  log("good i = %ld", i);
  log("");

  mops::BigInt i2 = mops::BigInt{1} << 32;
  log("good i2 = %ld", i2);
  log("");

  mops::BigInt i3 = i2 + i2;
  log("good i3 = %ld", i3);
  log("");

  int64_t j = int64_t{1} << 31;
  log("bad  j = %d", j);  // bug
  log("good j = %ld", j);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(bigint_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END();

  return 0;
}
