// mycpp/common.h
//
// A grab bag of definitions needed in multiple places.

#ifndef COMMON_H
#define COMMON_H

#include <assert.h>  // assert()
#include <stdarg.h>  // va_list, etc.
#include <stddef.h>  // max_align_t
#include <stdio.h>   // vprintf

// opt variants pass -D OPTIMIZED
#ifdef OPTIMIZED
  #define DCHECK(cond)
#else
  #define DCHECK(cond) assert(cond)
#endif

// TODO: all assert() should be DCHECK() or CHECK()
#define CHECK(cond) assert(cond)

#define FAIL(reason) assert(false)

enum Reason { kShouldNotGetHere, kNotImplemented };

// Workaround for macros that take templates
#define COMMA ,

// Prevent silent copies
#define DISALLOW_COPY_AND_ASSIGN(TypeName) \
  TypeName(TypeName&) = delete;            \
  void operator=(TypeName) = delete;

// log() is for hand-written code, not generated

inline void log(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  va_end(args);
  fputs("\n", stderr);
}

// I'm not sure why this matters but we get crashes when aligning to 8 bytes.
// That is annoying.
// Example: we get a crash in cpp/frontend_flag_spec.cc
// auto out = new flag_spec::_FlagSpecAndMore();
//
// https://stackoverflow.com/questions/52531695/int128-alignment-segment-fault-with-gcc-o-sse-optimize
constexpr int kMask = alignof(max_align_t) - 1;  // e.g. 15 or 7

// Align returned pointers to the worst case of 8 bytes (64-bit pointers)
inline size_t aligned(size_t n) {
  // https://stackoverflow.com/questions/2022179/c-quick-calculation-of-next-multiple-of-4
  // return (n + 7) & ~7;
  return (n + kMask) & ~kMask;
}

#define KiB(bytes) ((bytes)*1024)
#define MiB(bytes) (KiB(bytes) * 1024)
#define GiB(bytes) (MiB(bytes) * 1024)

const int kMaxRoots = KiB(4);

// Used by both Str and List slicing.  3 adjustments:
// 1. begin: negative, or greater than len
// 2. end: negative, or greater than len
// 3. begin > end means empty slice

#define SLICE_ADJUST(begin, end, len) \
  if (begin < 0) {                    \
    begin += len;                     \
    if (begin < 0) {                  \
      begin = 0;                      \
    }                                 \
  } else if (begin > len) {           \
    begin = len;                      \
  }                                   \
  if (end < 0) {                      \
    end += len;                       \
    if (end < 0) {                    \
      end = 0;                        \
    }                                 \
  } else if (end > len) {             \
    end = len;                        \
  }                                   \
  if (begin > end) {                  \
    end = begin;                      \
  }

#endif  // COMMON_H
