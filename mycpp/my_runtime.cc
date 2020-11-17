// my_runtime.cc

#include "my_runtime.h"

#include <cstdarg>  // va_list, etc.

GLOBAL_STR(kEmptyString, "");
my_runtime::BufWriter gBuf;

// Like print(..., file=sys.stderr), but Python code explicitly calls it.
void println_stderr(Str* s) {
  fputs(s->data_, stderr);  // it's NUL terminated
  fputs("\n", stderr);
}

// Copied from mylib.cc.
// TODO:
// - I think we can assert that len(old) == 1 for now.
Str* Str::replace(Str* old, Str* new_str) {
  const char* old_data = old->data_;
  const char* last_possible = data_ + len(this) - len(old);

  const char* p_this = data_;  // advances through 'this'

  // First pass to calculate the new length
  int replace_count = 0;
  while (p_this < last_possible) {
    // cstring-TODO: Don't use strstr()
    const char* next = strstr(p_this, old_data);
    if (next == nullptr) {
      break;
    }
    replace_count++;
    p_this = next + len(old);  // skip past
  }

  // log("done %d", replace_count);

  if (replace_count == 0) {
    return this;  // Reuse the string if there were no replacements
  }

  int length =
      len(this) - (replace_count * len(old)) + (replace_count * len(new_str));

  // TODO: Do NewStr(len) here, and then the data_ member
  char* tmp = static_cast<char*>(malloc(length + 1));  // +1 for NUL

  const char* new_data = new_str->data_;
  const size_t new_len = len(new_str);

  // Second pass to copy into new 'result'
  p_this = data_;
  char* p_result = tmp;  // advances through 'result'

  for (int i = 0; i < replace_count; ++i) {
    const char* next = strstr(p_this, old_data);
    assert(p_this != nullptr);
    size_t n = next - p_this;

    memcpy(p_result, p_this, n);  // Copy from 'this'
    p_result += n;

    memcpy(p_result, new_data, new_len);  // Copy from new_str
    p_result += new_len;

    p_this = next + len(old);
  }
  memcpy(p_result, p_this,
         data_ + len(this) - p_this);  // Copy the rest of 'this'
  tmp[length] = '\0';                  // NUL terminate

  // NOTE: This copies the buffer
  Str* s = NewStr(tmp);
  free(tmp);
  return s;
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
