#ifdef LEAKY_BINDINGS
  #include "mycpp/mylib_old.h"
using gc_heap::StackRoots;  // no-op
using mylib::AllocStr;
#else
  #include "mycpp/gc_builtins.h"
  #include "mycpp/gc_types.h"
using gc_heap::kEmptyString;
using gc_heap::StackRoots;
using gc_heap::Str;
#endif

#include <ctype.h>  // isalpha(), isdigit()

#ifndef LEAKY_BINDINGS
namespace gc_heap {
#endif

enum class StripWhere {
  Left,
  Right,
  Both,
};

const int kWhitespace = -1;

bool OmitChar(uint8_t ch, int what) {
  if (what == kWhitespace) {
    return isspace(ch);
  } else {
    return what == ch;
  }
}

// StripAny is modeled after CPython's do_strip() in stringobject.c, and can
// implement 6 functions:
//
//   strip / lstrip / rstrip
//   strip(char) / lstrip(char) / rstrip(char)
//
// Args:
//   where: which ends to strip from
//   what: kWhitespace, or an ASCII code 0-255

Str* StripAny(Str* s, StripWhere where, int what) {
  StackRoots _roots({&s});

  int length = len(s);
  const char* char_data = s->data();

  int i = 0;
  if (where != StripWhere::Right) {
    while (i < length && OmitChar(char_data[i], what)) {
      i++;
    }
  }

  int j = length;
  if (where != StripWhere::Left) {
    do {
      j--;
    } while (j >= i && OmitChar(char_data[j], what));
    j++;
  }

  if (i == j) {  // Optimization to reuse existing object
    return kEmptyString;
  }

  if (i == 0 && j == length) {  // nothing stripped
    return s;
  }

  // Note: makes a copy in leaky version, and will in GC version too
  int new_len = j - i;
  Str* result = AllocStr(new_len);
  memcpy(result->data(), s->data() + i, new_len);
  return result;
}

Str* Str::strip() {
  return StripAny(this, StripWhere::Both, kWhitespace);
}

// Used for CommandSub in osh/cmd_exec.py
Str* Str::rstrip(Str* chars) {
  assert(len(chars) == 1);
  int c = chars->data_[0];
  return StripAny(this, StripWhere::Right, c);
}

Str* Str::rstrip() {
  return StripAny(this, StripWhere::Right, kWhitespace);
}

#if 0
Str* Str::lstrip(Str* chars) {
  assert(len(chars) == 1);
  int c = chars->data_[0];
  return StripAny(this, StripWhere::Left, c);
}

Str* Str::lstrip() {
  return StripAny(this, StripWhere::Left, kWhitespace);
}
#endif

#ifndef LEAKY_BINDINGS
}  // namespace gc_heap
#endif
