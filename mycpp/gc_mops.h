// gc_mops.h - corresponds to mycpp/mops.py

#ifndef MYCPP_GC_MOPS_H
#define MYCPP_GC_MOPS_H

#include <stdint.h>

#include "mycpp/common.h"  // DCHECK
#include "mycpp/gc_tuple.h"

class BigStr;

namespace mops {

// BigInt library
// TODO: Make it arbitrary size.  Right now it's int64_t, which is distinct
// from int.

typedef int64_t BigInt;

// For convenience
extern const BigInt ZERO;
extern const BigInt ONE;
extern const BigInt MINUS_ONE;
extern const BigInt MINUS_TWO;

BigStr* ToStr(BigInt b);
BigStr* ToOctal(BigInt b);
BigStr* ToHexUpper(BigInt b);
BigStr* ToHexLower(BigInt b);

BigInt FromStr(BigStr* s, int base = 10);
Tuple2<bool, BigInt> FromFloat(double f);

inline int BigTruncate(BigInt b) {
  return static_cast<int>(b);
}

inline BigInt IntWiden(int b) {
  return static_cast<BigInt>(b);
}

inline BigInt FromC(int64_t i) {
  return i;
}

inline BigInt FromBool(bool b) {
  return b ? BigInt(1) : BigInt(0);
}

inline double ToFloat(BigInt b) {
  return static_cast<double>(b);
}

inline BigInt Negate(BigInt b) {
  return -b;
}

inline BigInt Add(BigInt a, BigInt b) {
  return a + b;
}

inline BigInt Sub(BigInt a, BigInt b) {
  return a - b;
}

inline BigInt Mul(BigInt a, BigInt b) {
  return a * b;
}

inline BigInt Div(BigInt a, BigInt b) {
  // Same check as in mops.py
  DCHECK(b != 0);  // divisor can't be zero
  return a / b;
}

inline BigInt Rem(BigInt a, BigInt b) {
  // Same check as in mops.py
  DCHECK(b != 0);  // divisor can't be zero
  return a % b;
}

inline bool Equal(BigInt a, BigInt b) {
  return a == b;
}

inline bool Greater(BigInt a, BigInt b) {
  return a > b;
}

inline BigInt LShift(BigInt a, BigInt b) {
  DCHECK(b >= 0);
  return a << b;
}

inline BigInt RShift(BigInt a, BigInt b) {
  DCHECK(b >= 0);
  return a >> b;
}

inline BigInt BitAnd(BigInt a, BigInt b) {
  return a & b;
}

inline BigInt BitOr(BigInt a, BigInt b) {
  return a | b;
}

inline BigInt BitXor(BigInt a, BigInt b) {
  return a ^ b;
}

inline BigInt BitNot(BigInt a) {
  return ~a;
}

}  // namespace mops

#endif  // MYCPP_GC_MOPS_H
