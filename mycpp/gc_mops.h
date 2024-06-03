// gc_mops.h - corresponds to mycpp/mops.py

#ifndef MYCPP_GC_MOPS_H
#define MYCPP_GC_MOPS_H

#include <stdint.h>

#include "mycpp/common.h"  // DCHECK

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

BigStr* ToStr(BigInt b);
BigInt FromStr(BigStr* s, int base = 10);

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

inline float ToFloat(BigInt b) {
  // TODO: test this
  return static_cast<float>(b);
}

inline BigInt FromFloat(float f) {
  // TODO: test this
  return static_cast<BigInt>(f);
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
  // Is the behavior of negative values defined in C++?  Avoid difference with
  // Python.
  DCHECK(a >= 0);
  DCHECK(b >= 0);
  return a / b;
}

inline BigInt Rem(BigInt a, BigInt b) {
  // Is the behavior of negative values defined in C++?  Avoid difference with
  // Python.
  DCHECK(a >= 0);
  DCHECK(b >= 0);
  return a % b;
}

inline bool Equal(BigInt a, BigInt b) {
  return a == b;
}

inline bool Greater(BigInt a, BigInt b) {
  return a > b;
}

inline BigInt LShift(BigInt a, BigInt b) {
  return a << b;
}

inline BigInt RShift(BigInt a, BigInt b) {
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
