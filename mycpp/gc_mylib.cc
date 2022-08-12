// gc_mylib.cc

#include "gc_mylib.h"

#include <errno.h>
#include <unistd.h>  // isatty

#include "gc_builtins.h"

mylib::BufWriter gBuf;

namespace mylib {

Tuple2<Str*, Str*> split_once(Str* s, Str* delim) {
  StackRoots _roots({&s, &delim});

  assert(len(delim) == 1);

  const char* start = s->data_;  // note: this pointer may move
  char c = delim->data_[0];
  int length = len(s);

  const char* p = static_cast<const char*>(memchr(start, c, length));

  if (p) {
    int len1 = p - start;
    int len2 = length - len1 - 1;  // -1 for delim

    Str* s1 = nullptr;
    Str* s2 = nullptr;
    StackRoots _roots({&s1, &s2});
    // Allocate together to avoid 's' moving in between
    s1 = AllocStr(len1);
    s2 = AllocStr(len2);

    memcpy(s1->data_, s->data_, len1);
    memcpy(s2->data_, s->data_ + len1 + 1, len2);

    return Tuple2<Str*, Str*>(s1, s2);
  } else {
    return Tuple2<Str*, Str*>(s, nullptr);
  }
}

}  // namespace mylib
