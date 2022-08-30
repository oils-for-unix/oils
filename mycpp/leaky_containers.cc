#ifdef OLDSTL_BINDINGS
  #include "mycpp/oldstl_containers.h"
#else
  #include "mycpp/gc_builtins.h"
  #include "mycpp/gc_containers.h"
#endif

#include "mycpp/list_str_impl.h"
#include "mycpp/comparator_impls.h"

#include <ctype.h>  // isalpha(), isdigit()

GLOBAL_STR(kEmptyString, "");

int Str::find(Str* needle, int pos) {
  int len_ = len(this);
  assert(len(needle) == 1);  // Oil's usage
  char c = needle->data_[0];
  for (int i = pos; i < len_; ++i) {
    if (data_[i] == c) {
      return i;
    }
  }
  return -1;
}

int Str::rfind(Str* needle) {
  int len_ = len(this);
  assert(len(needle) == 1);  // Oil's usage
  char c = needle->data_[0];
  for (int i = len_ - 1; i >= 0; --i) {
    if (data_[i] == c) {
      return i;
    }
  }
  return -1;
}

bool Str::isdigit() {
  int n = len(this);
  if (n == 0) {
    return false;  // special case
  }
  for (int i = 0; i < n; ++i) {
    if (!::isdigit(data_[i])) {
      return false;
    }
  }
  return true;
}

bool Str::isalpha() {
  int n = len(this);
  if (n == 0) {
    return false;  // special case
  }
  for (int i = 0; i < n; ++i) {
    if (!::isalpha(data_[i])) {
      return false;
    }
  }
  return true;
}

// e.g. for osh/braces.py
bool Str::isupper() {
  int n = len(this);
  if (n == 0) {
    return false;  // special case
  }
  for (int i = 0; i < n; ++i) {
    if (!::isupper(data_[i])) {
      return false;
    }
  }
  return true;
}

bool Str::startswith(Str* s) {
  int n = len(s);
  if (n > len(this)) {
    return false;
  }
  return memcmp(data_, s->data_, n) == 0;
}

bool Str::endswith(Str* s) {
  int len_s = len(s);
  int len_this = len(this);
  if (len_s > len_this) {
    return false;
  }
  const char* start = data_ + len_this - len_s;
  return memcmp(start, s->data_, len_s) == 0;
}

// Get a string with one character
Str* Str::index_(int i) {
  int len_ = len(this);
  if (i < 0) {
    i = len_ + i;
  }
  assert(i >= 0);
  assert(i < len_);  // had a problem here!

  char* buf = static_cast<char*>(malloc(2));
  buf[0] = data_[i];
  buf[1] = '\0';
  return CopyBufferIntoNewStr(buf, 1);
}

// s[begin:end]
Str* Str::slice(int begin, int end) {
  int len_ = len(this);
  begin = std::min(begin, len_);
  end = std::min(end, len_);

  assert(begin <= len_);
  assert(end <= len_);

  if (begin < 0) {
    begin = len_ + begin;
  }

  if (end < 0) {
    end = len_ + end;
  }

  begin = std::min(begin, len_);
  end = std::min(end, len_);

  begin = std::max(begin, 0);
  end = std::max(end, 0);

  assert(begin >= 0);
  assert(begin <= len_);

  assert(end >= 0);
  assert(end <= len_);

  int new_len = end - begin;

  // Tried to use std::clamp() here but we're not compiling against cxx-17
  new_len = std::max(new_len, 0);
  new_len = std::min(new_len, len_);

  /* printf("len(%d) [%d, %d] newlen(%d)\n",  len_, begin, end, new_len); */

  assert(new_len >= 0);
  assert(new_len <= len_);

  char* buf = static_cast<char*>(malloc(new_len + 1));
  memcpy(buf, data_ + begin, new_len);

  buf[new_len] = '\0';
  return CopyBufferIntoNewStr(buf, new_len);
}

// s[begin:]
Str* Str::slice(int begin) {
  int len_ = len(this);
  if (begin == 0) {
    return this;  // s[i:] where i == 0 is common in here docs
  }
  if (begin < 0) {
    begin = len_ + begin;
  }
  return slice(begin, len_);
}

// Used by 'help' builtin and --help, neither of which translate yet.

List<Str*>* Str::splitlines(bool keep) {
  assert(keep == true);
  NotImplemented();
}

Str* Str::upper() {
  int len_ = len(this);
  Str* result = AllocStr(len_);
  char* buffer = result->data();
  for (int char_index = 0; char_index < len_; ++char_index) {
    buffer[char_index] = toupper(data_[char_index]);
  }
  return result;
}

Str* Str::lower() {
  int len_ = len(this);
  Str* result = AllocStr(len_);
  char* buffer = result->data();
  for (int char_index = 0; char_index < len_; ++char_index) {
    buffer[char_index] = tolower(data_[char_index]);
  }
  return result;
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
      this_len - (replace_count * old_len) + (replace_count * new_str_len);

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
  result[result_len] = '\0';                            // NUL terminate

  return CopyBufferIntoNewStr(result, result_len);
}

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

Str* Str::lstrip(Str* chars) {
  assert(len(chars) == 1);
  int c = chars->data_[0];
  return StripAny(this, StripWhere::Left, c);
}

Str* Str::lstrip() {
  return StripAny(this, StripWhere::Left, kWhitespace);
}

