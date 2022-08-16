#include "oldstl_containers.h"

Heap gHeap;

#include <errno.h>
#include <unistd.h>  // isatty

#include <cassert>
#include <cstdio>
#include <exception>  // std::exception

List<Str*>* Str::split(Str* sep) {
  assert(len(sep) == 1);  // we can only split one char
  char sep_char = sep->data_[0];

  if (len(this) == 0) {
    // weird case consistent with Python: ''.split(':') == ['']
    return NewList<Str*>({kEmptyString});
  }

  // log("--- split()");
  // log("data [%s]", data_);

  auto result = NewList<Str*>({});

  int n = len(this);
  const char* pos = data_;
  const char* end = data_ + n;

  // log("pos %p", pos);
  while (true) {
    // log("n %d, pos %p", n, pos);

    const char* new_pos = static_cast<const char*>(memchr(pos, sep_char, n));
    if (new_pos == nullptr) {
      result->append(StrFromC(pos, end - pos));  // rest of the string
      break;
    }
    int new_len = new_pos - pos;

    result->append(StrFromC(pos, new_len));
    n -= new_len + 1;
    pos = new_pos + 1;
    if (pos >= end) {  // separator was at end of string
      result->append(kEmptyString);
      break;
    }
  }

  return result;
}

#if 0
Str* Str::join(List<Str*>* items) {
  int length = 0;
  const std::vector<Str*>& v = items->v_;
  int num_parts = v.size();
  if (num_parts == 0) {  // " ".join([]) == ""
    return kEmptyString;
  }
  for (int i = 0; i < num_parts; ++i) {
    length += len(v[i]);
  }
  // add length of all the separators
  int len_ = len(this);
  length += len_ * (num_parts - 1);

  // log("length: %d", length);
  // log("v.size(): %d", v.size());

  char* result = static_cast<char*>(malloc(length + 1));
  char* p_result = result;  // advances through

  for (int i = 0; i < num_parts; ++i) {
    // log("i %d", i);
    if (i != 0 && len_) {             // optimize common case of ''.join()
      memcpy(p_result, data_, len_);  // copy the separator
      p_result += len_;
      // log("len_ %d", len_);
    }

    int n = len(v[i]);
    // log("n: %d", n);
    memcpy(p_result, v[i]->data_, n);  // copy the list item
    p_result += n;
  }

  result[length] = '\0';  // NUL terminator

  return CopyBufferIntoNewStr(result, length);
}
#endif

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
