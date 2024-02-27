#include "mycpp/gc_mops.h"

#include <errno.h>
#include <stdio.h>

#include "mycpp/gc_alloc.h"
#include "mycpp/gc_builtins.h"  // StringToInt64
#include "mycpp/gc_str.h"

namespace mops {

const BigInt ZERO = BigInt{0};
const BigInt ONE = BigInt{1};
const BigInt MINUS_ONE = BigInt{-1};

static const int kInt64BufSize = 32;  // more than twice as big as kIntBufSize

// Copied from gc_builtins - str(int i)
BigStr* ToStr(BigInt b) {
  BigStr* s = OverAllocatedStr(kInt64BufSize);
  int length = snprintf(s->data(), kInt64BufSize, "%ld", b);
  s->MaybeShrink(length);
  return s;
}

// Copied from gc_builtins - to_int()
BigInt FromStr(BigStr* s, int base) {
  int64_t i;
  if (StringToInt64(s->data_, len(s), base, &i)) {
    return i;
  } else {
    throw Alloc<ValueError>();
  }
}

}  // namespace mops
