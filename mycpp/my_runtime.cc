// my_runtime.cc

#include "my_runtime.h"
#include "mylib2.h"  // BufWriter

#include <ctype.h>  // isspace(), isdigit()
#include <cstdarg>  // va_list, etc.

using gc_heap::StackRoots;
using gc_heap::kEmptyString;

// Translation of Python's print().
void print(Str* s) {
  int n = len(s);
  fwrite(s->data_, sizeof(char), n, stdout);
  fputs("\n", stdout);
}

// Like print(..., file=sys.stderr), but Python code explicitly calls it.
void println_stderr(Str* s) {
  int n = len(s);
  fwrite(s->data_, sizeof(char), n, stderr);
  fputs("\n", stderr);
}

// Helper for str_to_int() that doesn't use exceptions.
// Like atoi(), but with better error checking.
bool _str_to_int(Str* s, int* result, int base) {
  if (len(s) == 0) {
    return false;  // special case for empty string
  }

  char* p;                              // mutated by strtol
  long v = strtol(s->data_, &p, base);  // base 10

  switch (v) {
  case LONG_MIN:
    // log("underflow");
    return false;
  case LONG_MAX:
    // log("overflow");
    return false;
  }

  *result = v;

  // Return true if it consumed ALL characters.
  const char* end = s->data_ + len(s);

  // log("start %p   p %p   end %p", s->data_, p, end);
  if (p == end) {
    return true;
  }

  // Trailing space is OK!
  while (p < end) {
    if (!isspace(*p)) {
      return false;
    }
    p++;
  }
  return true;
}

// Python-like wrapper
int to_int(Str* s) {
  int i;
  if (_str_to_int(s, &i, 10)) {
    return i;
  } else {
    throw new ValueError();
  }
}

int to_int(Str* s, int base) {
  int i;
  if (_str_to_int(s, &i, base)) {
    return i;
  } else {
    throw new ValueError();
  }
}

Str* str_concat(Str* a, Str* b) {
  Str* result = nullptr;
  StackRoots _roots({&a, &b, &result});
  int len_a = len(a);
  int len_b = len(b);
  assert(len_a >= 0);
  assert(len_b >= 0);

  result = NewStr(len_a + len_b);
  char* buf = result->data_;
  memcpy(buf, a->data_, len_a);
  memcpy(buf + len_a, b->data_, len_b);

  assert(buf[len_a + len_b] == '\0');
  return result;
}

Str* str_repeat(Str* s, int times) {
  // Python allows -1 too, and Oil used that
  if (times <= 0) {
    return kEmptyString;
  }
  int part_len = len(s);
  int result_len = part_len * times;
  Str* result = NewStr(result_len);

  char* p_result = result->data_;
  for (int i = 0; i < times; i++) {
    memcpy(p_result, s->data_, part_len);
    p_result += part_len;
  }
  assert(p_result[result_len] == '\0');
  return result;
}

//
// Str methods
//

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

// Helper for lstrip() and strip()
int Str::_strip_left_pos() {
  assert(len(this) > 0);

  int i = 0;
  int n = len(this);
  bool done = false;
  while (i < n && !done) {
    switch (data_[i]) {
    case ' ':
    case '\t':
    case '\r':
    case '\n':
      i++;
    default:
      done = true;
      break;
    }
  }
  return i;
}

// Helper for rstrip() and strip()
int Str::_strip_right_pos() {
  assert(len(this) > 0);

  int last = len(this) - 1;
  int i = last;
  bool done = false;
  while (i > 0 && !done) {
    switch (data_[i]) {
    case ' ':
    case '\t':
    case '\r':
    case '\n':
      i--;
    default:
      done = true;
      break;
    }
  }
  return i;
}

Str* Str::strip() {
  int n = len(this);
  if (n == 0) {
    return this;
  }

  int left_pos = _strip_left_pos();
  int right_pos = _strip_right_pos();
  if (left_pos == 0 && right_pos == n - 1) {
    return this;
  }

  int new_len = right_pos - left_pos + 1;
  return NewStr(data_ + left_pos, new_len);  // Copy part of data
}

// Used for CommandSub in osh/cmd_exec.py
Str* Str::rstrip(Str* chars) {
  assert(0);
}

Str* Str::rstrip() {
  int n = len(this);
  if (n == 0) {
    return this;
  }
  int right_pos = _strip_right_pos();
  if (right_pos == n - 1) {  // nothing stripped
    return this;
  }
  return NewStr(data_, right_pos + 1);  // Copy part of data_
}

Str* Str::ljust(int width, Str* fillchar) {
  assert(len(fillchar) == 1);

  int length = len(this);
  int num_fill = width - length;
  if (num_fill < 0) {
    return this;
  } else {
    Str* result = NewStr(width);
    char c = fillchar->data_[0];
    memcpy(result->data_, data_, length);
    for (int i = length; i < width; ++i) {
      result->data_[i] = c;
    }
    assert(result->data_[width] == '\0');
    return result;
  }
}

Str* Str::rjust(int width, Str* fillchar) {
  assert(len(fillchar) == 1);

  int length = len(this);
  int num_fill = width - length;
  if (num_fill < 0) {
    return this;
  } else {
    Str* result = NewStr(width);
    char c = fillchar->data_[0];
    for (int i = 0; i < num_fill; ++i) {
      result->data_[i] = c;
    }
    memcpy(result->data_ + num_fill, data_, length);
    assert(result->data_[width] == '\0');
    return result;
  }
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
Str* Str::index(int i) {
  if (i < 0) {
    i = len(this) + i;
  }
  assert(i >= 0);
  assert(i < len(this));  // had a problem here!

  Str* result = NewStr(1);
  char* buf = result->data_;
  buf[0] = data_[i];
  assert(buf[1] == '\0');
  return result;
}

// s[begin:]
Str* Str::slice(int begin) {
  if (begin == 0) {
    return this;  // s[i:] where i == 0 is common in here docs
  }
  int length = len(this);
  if (begin < 0) {
    begin = length + begin;
  }
  return slice(begin, length);
}

// s[begin:end]
Str* Str::slice(int begin, int end) {
  if (begin < 0) {
    begin = len(this) + begin;
  }
  if (end < 0) {
    end = len(this) + end;
  }
  int new_len = end - begin;
  Str* result = NewStr(new_len);
  char* buf = result->data_;
  memcpy(buf, data_ + begin, new_len);
  assert(buf[new_len] == '\0');
  return result;
}

Str* Str::replace(Str* old, Str* new_str) {
  assert(len(old) == 1);  // Restriction that Oil code is OK with

  Str* self = this;       // must be a root!
  Str* result = nullptr;  // may not need to be a root, but make it robust

  // log("  self BEFORE %p", self);
  StackRoots _roots({&self, &old, &new_str, &result});

  int len_this = len(self);
  char old_char = old->data_[0];
  const char* p_this = self->data_;  // advances through 'this'
  const char* p_end = p_this + len_this;
  // printf("  p_this BEFORE %s\n", p_this);

  // First pass to calculate the new length
  int replace_count = 0;
  while (p_this < p_end) {
    if (*p_this == old_char) {
      replace_count++;
    }
    p_this++;
  }

  if (replace_count == 0) {
    return self;  // Reuse the string if there were no replacements
  }

  int result_len =
      len_this - (replace_count * len(old)) + (replace_count * len(new_str));

  // Second pass to copy into new 'result'
  result = NewStr(result_len);
  // log("  alloc result = %p", result);
  // log("  result = %p", result);
  // log("  self AFTER %p", self);

  const char* new_data = new_str->data_;
  const size_t new_len = len(new_str);

  p_this = self->data_;  // back to beginning
  // printf("  p_this AFTER %p\n", p_this);
  p_end = p_this + len_this;  // Must be rebound AFTER Alloc<>!

  char* p_result = result->data_;  // advances through 'result'

  // log("  p_this = %p, p_end %p", p_this, p_end);
  while (p_this < p_end) {
    // log("  *p_this [%d]", *p_this);
    if (*p_this == old_char) {
      memcpy(p_result, new_data, new_len);  // Copy from new_str
      p_this++;
      p_result += new_len;
    } else {
      *p_result = *p_this;
      p_this++;
      p_result++;
    }
  }
  assert(result->data_[result_len] == '\0');  // buffer should have been zero'd
  return result;
}

List<Str*>* Str::split(Str* sep) {
  assert(len(sep) == 1);  // we can only split one char
  char sep_char = sep->data_[0];

  int length = len(this);
  if (length == 0) {
    // weird case consistent with Python: ''.split(':') == ['']
    return Alloc<List<Str*>>(std::initializer_list<Str*>{kEmptyString});
  }

  auto result = Alloc<List<Str*>>();

  int n = length;
  const char* pos = data_;
  const char* end = data_ + length;

  while (true) {
    const char* new_pos = static_cast<const char*>(memchr(pos, sep_char, n));
    if (new_pos == nullptr) {
      result->append(NewStr(pos, end - pos));  // rest of the string
      break;
    }
    int new_len = new_pos - pos;

    result->append(NewStr(pos, new_len));
    n -= new_len + 1;
    pos = new_pos + 1;
    if (pos >= end) {  // separator was at end of string
      result->append(kEmptyString);
      break;
    }
  }
  return result;
}

Str* Str::join(List<Str*>* items) {
  Str* self = this;       // must be a root!
  Str* result = nullptr;  // may not need to be a root, but make it robust

  StackRoots _roots({&self, &result, &items});

  int result_len = 0;
  int num_parts = len(items);
  if (num_parts == 0) {  // " ".join([]) == ""
    return kEmptyString;
  }
  for (int i = 0; i < num_parts; ++i) {
    result_len += len(items->index(i));
  }
  int sep_len = len(self);
  // add length of all the separators
  result_len += sep_len * (num_parts - 1);

  // log("len: %d", len);
  // log("v.size(): %d", v.size());

  result = NewStr(result_len);
  char* p_result = result->data_;  // advances through

  for (int i = 0; i < num_parts; ++i) {
    // log("i %d", i);
    if (i != 0 && sep_len) {             // optimize common case of ''.join()
      memcpy(p_result, data_, sep_len);  // copy the separator
      p_result += sep_len;
      // log("len_ %d", len_);
    }

    int n = len(items->index(i));
    if (n < 0) {
      log("n: %d", n);
      assert(0);
    }
    memcpy(p_result, items->index(i)->data_, n);  // copy the list item
    p_result += n;
  }

  assert(p_result[result_len] == '\0');  // GC should zero it
  return result;
}

Str* repr(Str* s) {
  mylib::BufWriter f;
  f.format_r(s);
  return f.getvalue();
}
