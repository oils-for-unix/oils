#include <ctype.h>  // isalpha(), isdigit()

#include "mycpp/runtime.h"

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

  Str* result = NewStr(1);
  result->data_[0] = data_[i];
  return result;
}

// s[begin:end]
Str* Str::slice(int begin, int end) {
  RootingScope _r;

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

  Str* result = NewStr(new_len);
  memcpy(result->data_, data_ + begin, new_len);

  gHeap.RootOnReturn(result);  // return value rooting
  return result;
}

// s[begin:]
Str* Str::slice(int begin) {
  // RootingScope omitted because PASS THROUGH
  // log("slice(begin) -> %d frames", gHeap.root_set_.NumFrames());

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
  Str* result = NewStr(len_);
  char* buffer = result->data();
  for (int char_index = 0; char_index < len_; ++char_index) {
    buffer[char_index] = toupper(data_[char_index]);
  }
  return result;
}

Str* Str::lower() {
  int len_ = len(this);
  Str* result = NewStr(len_);
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
    Str* result = NewStr(width);
    char c = fillchar->data_[0];
    memcpy(result->data_, data_, len_);
    for (int i = len_; i < width; ++i) {
      result->data_[i] = c;
    }
    return result;
  }
}

Str* Str::rjust(int width, Str* fillchar) {
  assert(len(fillchar) == 1);

  int len_ = len(this);
  int num_fill = width - len_;
  if (num_fill < 0) {
    return this;
  } else {
    Str* result = NewStr(width);
    char c = fillchar->data_[0];
    for (int i = 0; i < num_fill; ++i) {
      result->data_[i] = c;
    }
    memcpy(result->data_ + num_fill, data_, len_);
    return result;
  }
}

Str* Str::replace(Str* old, Str* new_str) {
  StackRoots _roots0({&old, &new_str});

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

  Str* result = NewStr(result_len);
  StackRoots _roots1({&result});

  const char* new_data = new_str->data_;
  const size_t new_len = new_str_len;

  // Second pass: Copy pieces into 'result'
  p_this = data_;                  // back to beginning
  char* p_result = result->data_;  // advances through 'result'

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
  return result;
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
  Str* result = NewStr(new_len);
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

Str* Str::join(List<Str*>* items) {
  auto self = this;
  StackRoots _roots({&self, &items});

  int length = 0;

  int num_parts = len(items);
  if (num_parts == 0) {  // " ".join([]) == ""
    return kEmptyString;
  }
  for (int i = 0; i < num_parts; ++i) {
    length += len(items->index_(i));
  }
  // add length of all the separators
  int len_ = len(self);
  length += len_ * (num_parts - 1);

  Str* result = NewStr(length);
  char* p_result = result->data_;  // advances through

  for (int i = 0; i < num_parts; ++i) {
    // log("i %d", i);
    if (i != 0 && len_) {             // optimize common case of ''.join()
      memcpy(p_result, data_, len_);  // copy the separator
      p_result += len_;
      // log("len_ %d", len_);
    }

    int n = len(items->index_(i));
    // log("n: %d", n);
    memcpy(p_result, items->index_(i)->data_, n);  // copy the list item
    p_result += n;
  }

  return result;
}

int find_next(const char* haystack, int starting_index, int end_index,
              const char needle) {
  int result = end_index;
  for (int i = starting_index; i < end_index; ++i) {
    if (haystack[i] == needle) {
      result = i;
      break;
    }
  }
  return result;
}

Str* NewStrFromHeapStr(Str* src, int new_len, int start_index = 0) {
  StackRoots _roots({&src});

  Str* result = NewStr(new_len);
  assert((start_index + new_len) <= len(src));
  memcpy(result->data_, src->data_ + start_index, new_len);

  return result;
}

List<Str*>* Str::split(Str* sep) {
  assert(len(sep) == 1);  // we can only split one char
  char sep_char = sep->data_[0];

  auto self = this;
  List<Str*>* result = nullptr;

  StackRoots _roots({&self, &result});

  if (len(self) == 0) {
    // weird case consistent with Python: ''.split(':') == ['']
    return NewList<Str*>({kEmptyString});
  }

  result = NewList<Str*>({});

  int n = len(self);
  int pos = 0;
  int end = n;

  while (true) {
    // NOTE(Jesse): Perfect use case for BoundedBuffer
    int new_pos = find_next(self->data_, pos, end, sep_char);
    assert(new_pos >= pos);
    assert(new_pos <= end);

    if (new_pos == end) {
      Str* to_push = NewStrFromHeapStr(self, end - pos, pos);
      result->append(to_push);  // StrFromC(self->data_+pos, end - pos));  //
                                // rest of the string
      break;
    }

    int new_len = new_pos - pos;
    Str* to_push = NewStrFromHeapStr(self, new_len, pos);
    result->append(to_push);

    pos = new_pos + 1;
    if (pos >= end) {  // separator was at end of string
      result->append(kEmptyString);
      break;
    }
  }

  return result;
}
