#include <set>
#include <unordered_set>

#include "mycpp/common.h"
#include "vendor/greatest.h"

// Make sure we don't have the "hash pileup" problem
TEST unordered_set_bucket_test() {
  std::unordered_set<void *> set;
  // 1 bucket!
  log("bucket_count = %d", set.bucket_count());

  for (int i = 0; i < 1000; ++i) {
    void *p = malloc(1);
    // log("p = %p", p);

    std::hash<void *> hasher;
    int h = hasher(p);
    // This is just the low bits!
    // log("std::hash<void*>(pp) = %x", h);
    (void)h;

    set.insert(p);
    log("bucket %d", set.bucket(p));
  }
  // 1493 buckets, avoids power of 2 problem
  log("bucket_count = %d", set.bucket_count());

  PASS();
}

// Benchmark to test hashing against malloc()
TEST hash_speed_test() {
  std::unordered_set<void *> hash_set;
  std::set<void *> tree_set;
  int n = 10e3;  // change to 10e6 for significant benchmark
  // int n = 10e6;
  for (int i = 0; i < n; ++i) {
    // TODO: use random size workload too
    void *p = malloc(1);
    hash_set.insert(p);
    tree_set.insert(p);
  }
  log("hash_set size = %d", hash_set.size());
  log("bucket_count = %d", hash_set.bucket_count());
  log("tree_set size = %d", tree_set.size());

  PASS();
}

void do_mod(int n, int divisor) {
  int sum = 0;
  for (int i = 0; i < n; ++i) {
    sum += i % divisor;
  }
  log("sum = %d", sum);
}

TEST modulus_benchmark() {
  // 830 ms
  // do_mod(1<<30, 8);

  // 1.11 s
  // do_mod(1<<30, 7);

  // 900 ms seconds
  do_mod(1 << 30, 6);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char **argv) {
  // gHeap.Init(MiB(64));

  GREATEST_MAIN_BEGIN();

  RUN_TEST(unordered_set_bucket_test);
  RUN_TEST(hash_speed_test);
  // RUN_TEST(modulus_benchmark);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
