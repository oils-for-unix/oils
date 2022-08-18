#include "oldstl_containers.h"

Heap gHeap;

#include <errno.h>
#include <unistd.h>  // isatty

#include <cassert>
#include <cstdio>
#include <exception>  // std::exception

#include "cpp/aligned.h"
#include "mycpp/comparators.h"

namespace mylib {

Tuple2<Str*, Str*> split_once(Str* s, Str* delim) {
  assert(len(delim) == 1);

  const char* start = s->data_;
  char c = delim->data_[0];
  int length = len(s);

  const char* p = static_cast<const char*>(memchr(start, c, length));

  if (p) {
    // NOTE: Using SHARED SLICES, not memcpy() like some other functions.
    int len1 = p - start;
    Str* first = ::StrFromC(start, len1);
    Str* second = ::StrFromC(p + 1, length - len1 - 1);
    return Tuple2<Str*, Str*>(first, second);
  } else {
    return Tuple2<Str*, Str*>(s, nullptr);
  }
}

}  // namespace mylib

//
// Free functions
//

Str* repr(Str* s) {
  mylib::BufWriter f;
  f.format_r(s);
  return f.getvalue();
}

//
// Formatter
//

mylib::BufWriter gBuf;
