// common.h
//
// A grab bag of definitions needed in multiple places.

#ifndef COMMON_H
#define COMMON_H

#include <cstdarg>  // va_list, etc.
#include <cstdio>   // vprintf

// TODO(Jesse): Put NotImplemented on a compile-time switch such that we cannot
// make a release build if we're not finished implementing the interpreter.
// ie.
//
// #if OIL_INTERNAL
//   #define NotImplemented() assert(!"Not Implemented")
// #else
//   #define NotImplemented() NOT IMPLENTED !!! // Intentionally a compile error
// #endif
//
//
#define NotImplemented() assert(!"Not Implemented")
#define InvalidCodePath() assert(!"Invalid Code Path")

#define Kilobytes(n) (n << 10)
#define Megabytes(n) (n << 20)
#define Gigabytes(n) (n << 30)
#define Terabytes(n) ((uint64_t)((n##ul) << 40))

static_assert(Kilobytes(1) == 1024, "");
static_assert(Megabytes(1) == Kilobytes(1)*1024, "");
static_assert(Gigabytes(1) == Megabytes(1)*1024, "");
static_assert(Terabytes(1) == Gigabytes(1)*1024ul, "");

// Prevent silent copies

#define DISALLOW_COPY_AND_ASSIGN(TypeName) \
  TypeName(TypeName&) = delete;            \
  void operator=(TypeName) = delete;

// log() is for hand-written code, not generated

inline void log(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vprintf(fmt, args);
  va_end(args);
  puts("");
}

namespace common {}  // namespace common

#endif  // COMMON_H
