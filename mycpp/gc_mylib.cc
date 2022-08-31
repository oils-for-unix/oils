// gc_mylib.cc

#include "mycpp/runtime.h"

#include <errno.h>
#include <unistd.h>  // isatty

mylib::BufWriter gBuf;


// NOTE(Jesse): This was literally the only thing left in gc_builtins.cc so I
// moved it here.  Not sure where it belongs, but it's only called from a
// single test.
Str* repr(Str* s) {
  mylib::BufWriter f;
  f.format_r(s);
  return f.getvalue();
}


namespace mylib {

/* template <typename K, typename V> */
/* void dict_remove(Dict<K, V>* haystack, K needle) */
/* { */
/*   ::dict_remove(haystack, needle); */
/* } */

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
