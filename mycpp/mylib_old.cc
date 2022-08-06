// mylib_old.cc

#include "mylib_old.h"
using mylib::CopyBufferIntoNewStr;

#include <errno.h>
#include <unistd.h>  // isatty

#include <cassert>
#include <cstdio>
#include <exception>  // std::exception

extern Str* kEmptyString; // = StrFromC("", 0);

// For cStringIO API
Str* mylib::BufWriter::getvalue() {
  if (data_) {
    Str* ret = CopyBufferIntoNewStr(data_, len_);
    reset();  // Invalidate this instance
    return ret;
  } else {
    // log('') translates to this
    // Strings are immutable so we can do this.
    return kEmptyString;
  }
}


List<Str*>* Str::split(Str* sep) {
  assert(len(sep) == 1);  // we can only split one char
  char sep_char = sep->data_[0];

  if (len(this) == 0) {
    // weird case consistent with Python: ''.split(':') == ['']
    return new List<Str*>({kEmptyString});
  }

  // log("--- split()");
  // log("data [%s]", data_);

  auto result = new List<Str*>({});

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

// Get a string with one character
Str* StrIter::Value() {
  char* buf = static_cast<char*>(malloc(2));
  buf[0] = s_->data_[i_];
  buf[1] = '\0';
  return CopyBufferIntoNewStr(buf, 1);
}

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
    Str* first = StrFromC(start, len1);
    Str* second = StrFromC(p + 1, length - len1 - 1);
    return Tuple2<Str*, Str*>(first, second);
  } else {
    return Tuple2<Str*, Str*>(s, nullptr);
  }
}

//
// LineReader
//

LineReader* gStdin;

#if 1
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
  return CopyBufferIntoNewStr(line, len);
}
#endif

// problem: most Str methods like index() and slice() COPY so they have a
// NUL terminator.
// log("%s") falls back on sprintf, so it expects a NUL terminator.
// It would be easier for us to just share.
Str* BufLineReader::readline() {
  const char* end = s_->data_ + len(s_);
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
  Str* line = CopyBufferIntoNewStr(result, len);

  // Easier way:
  // Str* line = CopyBufferIntoNewStr(pos_, new_pos - pos_);
  return line;
}

//
// Writer
//

Writer* gStdout;
Writer* gStderr;

void BufWriter::write(Str* s) {
  int orig_len = len_;
  len_ += len(s);

  // BUG: This is quadratic!

  // data_ is nullptr at first
  data_ = static_cast<char*>(realloc(data_, len_ + 1));

  // Append to the end
  memcpy(data_ + orig_len, s->data_, len(s));
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
  int upper_bound = len(s) * 4 + 2;

  // Extend the buffer
  data_ = static_cast<char*>(realloc(data_, len_ + upper_bound + 1));

  char quote = '\'';
  if (memchr(s->data_, '\'', len(s)) && !memchr(s->data_, '"', len(s))) {
    quote = '"';
  }
  char* p = data_ + len_;  // end of valid data

  // From PyString_Repr()
  *p++ = quote;
  for (int i = 0; i < len(s); ++i) {
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
  fwrite(s->data_, len(s), 1, f_);

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

//
// Formatter
//

mylib::BufWriter gBuf;

