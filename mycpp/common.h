// common.h
//
// A grab bag of definitions needed in multiple places.

#ifndef COMMON_H
#define COMMON_H

#include <cstdarg>  // va_list, etc.
#include <cstdio>   // vprintf

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
