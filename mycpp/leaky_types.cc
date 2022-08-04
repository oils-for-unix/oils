#ifdef LEAKY_BINDINGS
  #include "mycpp/mylib_old.h"
using gc_heap::StackRoots;  // no-op
using mylib::AllocStr;
using mylib::CopyBufferIntoNewStr;
#else
  #include "mycpp/gc_builtins.h"
  #include "mycpp/gc_types.h"
using gc_heap::kEmptyString;
using gc_heap::StackRoots;
using gc_heap::Str;
using gc_heap::CopyBufferIntoNewStr;
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

Str* Str::ljust(int width, Str* fillchar) {
  assert(len(fillchar) == 1);

  int len_ = len(this);
  int num_fill = width - len_;
  if (num_fill < 0) {
    return this;
  } else {
    char* buf = static_cast<char*>(malloc(width));
    char c = fillchar->data_[0];
    memcpy(buf, data_, len_);
    for (int i = len_; i < width; ++i) {
      buf[i] = c;
    }
    return CopyBufferIntoNewStr(buf, width);
  }
}

Str* Str::rjust(int width, Str* fillchar) {
  assert(len(fillchar) == 1);

  int len_ = len(this);
  int num_fill = width - len_;
  if (num_fill < 0) {
    return this;
  } else {
    char* buf = static_cast<char*>(malloc(width));
    char c = fillchar->data_[0];
    for (int i = 0; i < num_fill; ++i) {
      buf[i] = c;
    }
    memcpy(buf + num_fill, data_, len_);
    return CopyBufferIntoNewStr(buf, width);
  }
}

Str* Str::replace(Str* old, Str* new_str) {
  // log("replacing %s with %s", old_data, new_str->data_);

  const char* old_data = old->data_;
  int this_len = len(this);
  int old_len = len(old);
  const char* last_possible = data_ + this_len - old_len;

  const char* p_this = data_;  // advances through 'this'

  // First pass: Calculate number of replacements, and hence new length
  int replace_count = 0;
  while (p_this <= last_possible) {
    if (memcmp(p_this, old_data, old_len) == 0) {  // equal
      replace_count++;
      p_this += old_len;
    } else {
      p_this++;
    }
  }

  // log("replacements %d", replace_count);

  if (replace_count == 0) {
    return this;  // Reuse the string if there were no replacements
  }

  int new_str_len = len(new_str);
  int result_len =
      this_len - (replace_count * old_len) + (replace_count * new_str_len );

  char* result = static_cast<char*>(malloc(result_len + 1));  // +1 for NUL

  const char* new_data = new_str->data_;
  const size_t new_len = new_str_len;

  // Second pass: Copy pieces into 'result'
  p_this = data_;           // back to beginning
  char* p_result = result;  // advances through 'result'

  while (p_this <= last_possible) {
    // Note: would be more efficient if we remembered the match positions
    if (memcmp(p_this, old_data, old_len) == 0) {  // equal
      memcpy(p_result, new_data, new_len);         // Copy from new_str
      p_result += new_len;
      p_this += old_len;
    } else {  // copy 1 byte
      *p_result = *p_this;
      p_result++;
      p_this++;
    }
  }
  memcpy(p_result, p_this, data_ + this_len - p_this);  // last part of string
  result[result_len] = '\0';                        // NUL terminate

  return CopyBufferIntoNewStr(result, result_len);
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
