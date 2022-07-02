// time.h

#ifndef TIME_H
#define TIME_H

#include <time.h>

#include "mycpp/mylib_leaky.h"

#include "cpp/core_error.h"
#include "cpp/core_pyerror.h"

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
  Str* result = kEmptyString;

  assert(s->IsNulTerminated());

  tm* loc_time = ::localtime(&ts);

  const int buf_size = 1024;
  char buffer[buf_size] = {};

  if (int size_of_result = strftime(buffer, buf_size, s->data_, loc_time)) {
    result = new Str(buffer, size_of_result);
  } else {
   e_die(new Str("Call strftime failed. The result from the format string specified was too long to be accomodated."));
  }

  return result;
}

}  // namespace time_

#endif  // TIME_H
