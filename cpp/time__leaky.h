// time.h

#ifndef TIME_H
#define TIME_H

#include <time.h>

#include "cpp/core_error_leaky.h"
#include "cpp/core_pyerror_leaky.h"
#include "mycpp/mylib_leaky.h"
using mylib::CopyStr;
using mylib::OverAllocatedStr;

namespace time_ {

inline void tzset() {
  ::tzset();
}

inline time_t time() {
  return ::time(nullptr);
}

// NOTE(Jesse): time_t is specified to be an arithmetic type by C++. On most
// systems it's a 64-bit integer.  64 bits is used because 32 will overflow in
// 2038.  Someone on a comittee somewhere thought of that when moving to 64-bit
// architectures to prevent breaking ABI again; on 32-bit systems it's usually
// 32 bits.  Point being, using anything but the time_t typedef here could
// (unlikely, but possible) produce weird behavior.
inline time_t localtime(time_t ts) {
  tm* loc_time = ::localtime(&ts);
  time_t result = mktime(loc_time);
  return result;
}

inline Str* strftime(Str* s, time_t ts) {
  // TODO: may not work with mylib_leaky.h
  // https://github.com/oilshell/oil/issues/1221
  assert(s->IsNulTerminated());

  tm* loc_time = ::localtime(&ts);

  const int max_len = 1024;
  Str* result = OverAllocatedStr(max_len);
  int n = strftime(result->data(), max_len, s->data_, loc_time);
  if (n == 0) {
    // bash silently truncates on large format string like
    //   printf '%(%Y)T'
    // Oil doesn't mask errors
    // No error location info, but leaving it out points reliably to 'printf'
    e_die(CopyStr("strftime() result exceeds 1024 bytes"));
  }
  result->SetObjLenFromStrLen(n);
  return result;
}

}  // namespace time_

#endif  // TIME_H
