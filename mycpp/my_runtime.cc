// my_runtime.cc

#include "my_runtime.h"

#include <ctype.h>  // isspace()
#include <cstdarg>  // va_list, etc.

GLOBAL_STR(kEmptyString, "");
my_runtime::BufWriter gBuf;

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
  int len_a = len(a);
  int len_b = len(b);

  Str* result = NewStr(len_a + len_b);
  char* buf = result->data_;
  memcpy(buf, a->data_, len_a);
  memcpy(buf + len_a, b->data_, len_b);

  assert(buf[len_a + len_b] == '\0');
  return result;
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

  char old_char = old->data_[0];
  const char* p_this = data_;  // advances through 'this'
  const char* p_end = data_ + len(this);

  // First pass to calculate the new length
  int replace_count = 0;
  while (p_this < p_end) {
    if (*p_this == old_char) {
      replace_count++;
    }
    p_this++;
  }

  if (replace_count == 0) {
    return this;  // Reuse the string if there were no replacements
  }

  int length =
      len(this) - (replace_count * len(old)) + (replace_count * len(new_str));

  const char* new_data = new_str->data_;
  const size_t new_len = len(new_str);

  // Second pass to copy into new 'result'
  Str* result = NewStr(length);
  p_this = data_;                  // back to beginning
  char* p_result = result->data_;  // advances through 'result'

  while (p_this < p_end) {
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
  assert(result->data_[length] == '\0');  // buffer should have been zero'd
  return result;
}

namespace my_runtime {

Writer* gStdout;
Writer* gStderr;

void BufWriter::write(Str* s) {
  int orig_len = len_;
  int n = len(s);
  len_ += n;

  // BUG: This is quadratic!

  // data_ is nullptr at first
  data_ = static_cast<char*>(realloc(data_, len_ + 1));

  // Append to the end
  memcpy(data_ + orig_len, s->data_, n);
  data_[len_] = '\0';
}

void BufWriter::write_const(const char* s, int len) {
  int orig_len = len_;
  len_ += len;
  // data_ is nullptr at first
  data_ = static_cast<char*>(realloc(data_, len_ + 1));

  // Append to the end
  memcpy(data_ + orig_len, s, len);
  data_[len_] = '\0';
}

void BufWriter::format_s(Str* s) {
  this->write(s);
}

void BufWriter::format_d(int i) {
  // extend to the maximum size
  data_ = static_cast<char*>(realloc(data_, len_ + kIntBufSize));
  int len = snprintf(data_ + len_, kIntBufSize, "%d", i);
  // but record only the number of bytes written
  len_ += len;
}

// repr() calls this too
//
// TODO: This could be replaced with QSN?  The upper bound is greater there
// because of \u{}.
void BufWriter::format_r(Str* s) {
  // Worst case: \0 becomes 4 bytes as '\\x00', and then two quote bytes.
  int n = len(s);
  int upper_bound = n * 4 + 2;

  // Extend the buffer
  data_ = static_cast<char*>(realloc(data_, len_ + upper_bound + 1));

  char quote = '\'';
  if (memchr(s->data_, '\'', n) && !memchr(s->data_, '"', n)) {
    quote = '"';
  }
  char* p = data_ + len_;  // end of valid data

  // From PyString_Repr()
  *p++ = quote;
  for (int i = 0; i < n; ++i) {
    char c = s->data_[i];
    if (c == quote || c == '\\') {
      *p++ = '\\';
      *p++ = c;
    } else if (c == '\t') {
      *p++ = '\\';
      *p++ = 't';
    } else if (c == '\n') {
      *p++ = '\\';
      *p++ = 'n';
    } else if (c == '\r') {
      *p++ = '\\';
      *p++ = 'r';
    } else if (c < ' ' || c >= 0x7f) {
      sprintf(p, "\\x%02x", c & 0xff);
      p += 4;
    } else {
      *p++ = c;
    }
  }
  *p++ = quote;
  *p = '\0';

  len_ = p - data_;
  // Shrink the buffer.  This is valid usage and GNU libc says it can actually
  // release.
  data_ = static_cast<char*>(realloc(data_, len_ + 1));
}

}  // namespace my_runtime
