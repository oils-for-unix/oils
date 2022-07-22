// mylib_old.cc

#include "mylib_old.h"

#include <errno.h>
#include <unistd.h>  // isatty

#include <cassert>
#include <cstdio>
#include <exception>  // std::exception

Str* kEmptyString = new Str("", 0);

// Translation of Python's print().
void print(Str* s) {
  mylib::Str0 s0(s);
  fputs(s0.Get(), stdout);
  fputs("\n", stdout);
}

// Like print(..., file=sys.stderr), but Python code explicitly calls it.
void println_stderr(Str* s) {
  mylib::Str0 s0(s);
  fputs(s0.Get(), stderr);
  fputs("\n", stderr);
}

// NOTE:
// - Oil interpreter code only uses the very common case of len(old) == 1.
//   - But we probably want to expose this more general function to OIL USERS.
//   - We could have a special case for this like CPython.  It detects if
//   len(old) == len(new) as well.
// - Python replace() has a third 'count' argument we're not using.
Str* Str::replace(Str* old, Str* new_str) {
  // log("replacing %s with %s", old_data, new_str->data_);

  const char* old_data = old->data_;
  int old_len = old->len_;
  const char* last_possible = data_ + len_ - old_len;

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

  int result_len =
      this->len_ - (replace_count * old_len) + (replace_count * new_str->len_);

  char* result = static_cast<char*>(malloc(result_len + 1));  // +1 for NUL

  const char* new_data = new_str->data_;
  const size_t new_len = new_str->len_;

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
  memcpy(p_result, p_this, data_ + len_ - p_this);  // last part of string
  result[result_len] = '\0';                        // NUL terminate

  return new Str(result, result_len);
}

Str* Str::ljust(int width, Str* fillchar) {
  assert(len(fillchar) == 1);

  int num_fill = width - len_;
  if (num_fill < 0) {
    return this;
  } else {
    char* buf = static_cast<char*>(malloc(width + 1));
    char c = fillchar->data_[0];
    memcpy(buf, data_, len_);
    for (int i = len_; i < width; ++i) {
      buf[i] = c;
    }
    buf[width] = '\0';
    return new Str(buf, width);
  }
}

Str* Str::rjust(int width, Str* fillchar) {
  assert(len(fillchar) == 1);

  int num_fill = width - len_;
  if (num_fill < 0) {
    return this;
  } else {
    char* buf = static_cast<char*>(malloc(width + 1));
    char c = fillchar->data_[0];
    for (int i = 0; i < num_fill; ++i) {
      buf[i] = c;
    }
    memcpy(buf + num_fill, data_, len_);
    buf[width] = '\0';
    return new Str(buf, width);
  }
}

List<Str*>* Str::split(Str* sep) {
  assert(sep->len_ == 1);  // we can only split one char
  char sep_char = sep->data_[0];

  if (len_ == 0) {
    // weird case consistent with Python: ''.split(':') == ['']
    return new List<Str*>({kEmptyString});
  }

  // log("--- split()");
  // log("data [%s]", data_);

  auto result = new List<Str*>({});

  int n = len_;
  const char* pos = data_;
  const char* end = data_ + len_;

  // log("pos %p", pos);
  while (true) {
    // log("n %d, pos %p", n, pos);

    const char* new_pos = static_cast<const char*>(memchr(pos, sep_char, n));
    if (new_pos == nullptr) {
      result->append(new Str(pos, end - pos));  // rest of the string
      break;
    }
    int new_len = new_pos - pos;

    result->append(new Str(pos, new_len));
    n -= new_len + 1;
    pos = new_pos + 1;
    if (pos >= end) {  // separator was at end of string
      result->append(kEmptyString);
      break;
    }
  }

  return result;
}

List<Str*>* Str::splitlines(bool keep) {
  assert(keep == true);
  return nullptr;
}

Str* Str::join(List<Str*>* items) {
  int len = 0;
  const std::vector<Str*>& v = items->v_;
  int num_parts = v.size();
  if (num_parts == 0) {  // " ".join([]) == ""
    return kEmptyString;
  }
  for (int i = 0; i < num_parts; ++i) {
    len += v[i]->len_;
  }
  // add length of all the separators
  len += len_ * (num_parts - 1);

  // log("len: %d", len);
  // log("v.size(): %d", v.size());

  char* result = static_cast<char*>(malloc(len + 1));
  char* p_result = result;  // advances through

  for (int i = 0; i < num_parts; ++i) {
    // log("i %d", i);
    if (i != 0 && len_) {             // optimize common case of ''.join()
      memcpy(p_result, data_, len_);  // copy the separator
      p_result += len_;
      // log("len_ %d", len_);
    }

    int n = v[i]->len_;
    // log("n: %d", n);
    memcpy(p_result, v[i]->data_, n);  // copy the list item
    p_result += n;
  }

  result[len] = '\0';  // NUL terminator

  return new Str(result, len);
}

Str* Str::upper() {
  Str* result = mylib::AllocStr(len_);
  char* buffer = result->data();
  for (int char_index = 0; char_index < len_; ++char_index) {
    buffer[char_index] = toupper(data_[char_index]);
  }
  return result;
}

Str* Str::lower() {
  Str* result = mylib::AllocStr(len_);
  char* buffer = result->data();
  for (int char_index = 0; char_index < len_; ++char_index) {
    buffer[char_index] = tolower(data_[char_index]);
  }
  return result;
}

// Get a string with one character
Str* StrIter::Value() {
  char* buf = static_cast<char*>(malloc(2));
  buf[0] = s_->data_[i_];
  buf[1] = '\0';
  return new Str(buf, 1);
}

namespace mylib {

Tuple2<Str*, Str*> split_once(Str* s, Str* delim) {
  assert(delim->len_ == 1);

  const char* start = s->data_;
  char c = delim->data_[0];
  int len = s->len_;

  const char* p = static_cast<const char*>(memchr(start, c, len));

  if (p) {
    // NOTE: Using SHARED SLICES, not memcpy() like some other functions.
    int len1 = p - start;
    Str* first = new Str(start, len1);
    Str* second = new Str(p + 1, len - len1 - 1);
    return Tuple2<Str*, Str*>(first, second);
  } else {
    return Tuple2<Str*, Str*>(s, nullptr);
  }
}

//
// LineReader
//

LineReader* gStdin;

Str* CFileLineReader::readline() {
  char* line = nullptr;
  size_t allocated_size = 0;  // unused

  errno = 0;  // must be reset because we check it below!
  ssize_t len = getline(&line, &allocated_size, f_);
  if (len < 0) {
    // log("getline() result: %d", len);
    if (errno != 0) {
      // Unexpected error
      log("getline() error: %s", strerror(errno));
      throw new AssertionError(errno);
    }
    // Expected EOF
    return kEmptyString;
  }
  // log("len = %d", len);

  // Note: it's NUL terminated
  return new Str(line, len);
}

// problem: most Str methods like index() and slice() COPY so they have a
// NUL terminator.
// log("%s") falls back on sprintf, so it expects a NUL terminator.
// It would be easier for us to just share.
Str* BufLineReader::readline() {
  const char* end = s_->data_ + s_->len_;
  if (pos_ == end) {
    return kEmptyString;
  }

  const char* orig_pos = pos_;
  const char* new_pos = strchr(pos_, '\n');
  // log("pos_ = %s", pos_);
  int len;
  if (new_pos) {
    len = new_pos - pos_ + 1;  // past newline char
    pos_ = new_pos + 1;
  } else {  // leftover line
    len = end - pos_;
    pos_ = end;
  }

  char* result = static_cast<char*>(malloc(len + 1));
  memcpy(result, orig_pos, len);  // copy the list item
  result[len] = '\0';
  Str* line = new Str(result, len);

  // Easier way:
  // Str* line = new Str(pos_, new_pos - pos_);
  return line;
}

//
// Writer
//

Writer* gStdout;
Writer* gStderr;

void BufWriter::write(Str* s) {
  int orig_len = len_;
  len_ += s->len_;

  // BUG: This is quadratic!

  // data_ is nullptr at first
  data_ = static_cast<char*>(realloc(data_, len_ + 1));

  // Append to the end
  memcpy(data_ + orig_len, s->data_, s->len_);
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

void BufWriter::format_o(int i) {
  NotImplemented();
}

// repr() calls this too
//
// TODO: This could be replaced with QSN?  The upper bound is greater there
// because of \u{}.
void BufWriter::format_r(Str* s) {
  // Worst case: \0 becomes 4 bytes as '\\x00', and then two quote bytes.
  int upper_bound = s->len_ * 4 + 2;

  // Extend the buffer
  data_ = static_cast<char*>(realloc(data_, len_ + upper_bound + 1));

  char quote = '\'';
  if (memchr(s->data_, '\'', s->len_) && !memchr(s->data_, '"', s->len_)) {
    quote = '"';
  }
  char* p = data_ + len_;  // end of valid data

  // From PyString_Repr()
  *p++ = quote;
  for (int i = 0; i < s->len_; ++i) {
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

// void BufWriter::format_s(const char* s) {
//  this->write_const(s, strlen(s));
//}

void CFileWriter::write(Str* s) {
  // note: throwing away the return value
  fwrite(s->data_, s->len_, 1, f_);

  // Necessary for 'echo hi > x' to work.  Otherwise it gets buffered so the
  // write() happens AFTER ~ctx_Redirect().
  //
  // TODO: use write() directly to avoid buffering problems?  But we also want
  // fast command sub like ${.echo x}
  fflush(f_);
}

void CFileWriter::flush() {
  fflush(f_);
}

bool CFileWriter::isatty() {
  return ::isatty(fileno(f_));
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

Str* str_concat(Str* a, Str* b) {
  int new_len = a->len_ + b->len_;
  char* buf = static_cast<char*>(malloc(new_len + 1));

  int len_a = a->len_;
  memcpy(buf, a->data_, len_a);
  memcpy(buf + len_a, b->data_, b->len_);
  buf[new_len] = '\0';

  return new Str(buf, new_len);
}

// for os_path.join()
Str* str_concat3(Str* a, Str* b, Str* c) {
  int new_len = a->len_ + b->len_ + c->len_;
  char* buf = static_cast<char*>(malloc(new_len + 1));
  char* pos = buf;

  memcpy(pos, a->data_, a->len_);
  pos += a->len_;

  memcpy(pos, b->data_, b->len_);
  pos += b->len_;

  memcpy(pos, c->data_, c->len_);

  buf[new_len] = '\0';

  return new Str(buf, new_len);
}

Str* str_repeat(Str* s, int times) {
  // Python allows -1 too, and Oil used that
  if (times <= 0) {
    return kEmptyString;
  }
  int len = s->len_;
  int new_len = len * times;
  char* data = static_cast<char*>(malloc(new_len + 1));

  char* dest = data;
  for (int i = 0; i < times; i++) {
    memcpy(dest, s->data_, len);
    dest += len;
  }
  data[new_len] = '\0';
  return new Str(data, new_len);
}

// Helper for str_to_int() that doesn't use exceptions.
// Like atoi(), but with better error checking.
bool _str_to_int(Str* s, int* result, int base) {
  if (s->len_ == 0) {
    return false;  // special case for empty string
  }

  char* p;  // mutated by strtol

  mylib::Str0 s0(s);
  long v = strtol(s0.Get(), &p, base);  // base 10
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
  const char* end = s->data_ + s->len_;

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

//
// Formatter
//

mylib::BufWriter gBuf;
