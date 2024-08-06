#include "mycpp/gc_mops.h"

#include <errno.h>
#include <inttypes.h>  // PRIo64, PRIx64
#include <math.h>      // isnan(), isinf()
#include <stdio.h>

#include "mycpp/gc_alloc.h"
#include "mycpp/gc_builtins.h"  // StringToInt64
#include "mycpp/gc_str.h"

namespace mops {

const BigInt ZERO = BigInt{0};
const BigInt ONE = BigInt{1};
const BigInt MINUS_ONE = BigInt{-1};
const BigInt MINUS_TWO = BigInt{-2};  // for printf

static const int kInt64BufSize = 32;  // more than twice as big as kIntBufSize

// Note: Could also use OverAllocatedStr, but most strings are small?

// Similar to str(int i) in gc_builtins.cc

BigStr* ToStr(BigInt b) {
  char buf[kInt64BufSize];
  int len = snprintf(buf, kInt64BufSize, "%" PRId64, b);
  return ::StrFromC(buf, len);
}

BigStr* ToOctal(BigInt b) {
  char buf[kInt64BufSize];
  int len = snprintf(buf, kInt64BufSize, "%" PRIo64, b);
  return ::StrFromC(buf, len);
}

BigStr* ToHexUpper(BigInt b) {
  char buf[kInt64BufSize];
  int len = snprintf(buf, kInt64BufSize, "%" PRIX64, b);
  return ::StrFromC(buf, len);
}

BigStr* ToHexLower(BigInt b) {
  char buf[kInt64BufSize];
  int len = snprintf(buf, kInt64BufSize, "%" PRIx64, b);
  return ::StrFromC(buf, len);
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

Tuple2<bool, BigInt> FromFloat(double f) {
  if (isnan(f) || isinf(f)) {
    return Tuple2<bool, BigInt>(false, MINUS_ONE);
  }
#ifdef BIGINT
  // Testing that _bin/cxx-opt+bigint/ysh is actually different!
  log("*** BIGINT active ***");
#endif
  return Tuple2<bool, BigInt>(true, static_cast<BigInt>(f));
}

}  // namespace mops
