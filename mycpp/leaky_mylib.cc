// clang-format off
#include "mycpp/myerror.h"
// clang-format on

#include <errno.h>
#include <stdio.h>
#include <unistd.h>  // isatty

#include "mycpp/runtime.h"

namespace mylib {

// NOTE: split_once() was in gc_mylib, and is likely not leaky
Tuple2<Str*, Str*> split_once(Str* s, Str* delim) {
  StackRoots _roots({&s, &delim});

  assert(len(delim) == 1);

  const char* start = s->data_;  // note: this pointer may move
  char c = delim->data_[0];
  int length = len(s);

  const char* p = static_cast<const char*>(memchr(start, c, length));

  if (p) {
    int len1 = p - start;
    int len2 = length - len1 - 1;  // -1 for delim

    Str* s1 = nullptr;
    Str* s2 = nullptr;
    StackRoots _roots({&s1, &s2});
    // Allocate together to avoid 's' moving in between
    s1 = AllocStr(len1);
    s2 = AllocStr(len2);

    memcpy(s1->data_, s->data_, len1);
    memcpy(s2->data_, s->data_ + len1 + 1, len2);

    return Tuple2<Str*, Str*>(s1, s2);
  } else {
    return Tuple2<Str*, Str*>(s, nullptr);
  }
}

Str* BufWriter::getvalue() {
  if (data_) {
    Str* ret = ::StrFromC(data_, len_);
    reset();  // Invalidate this instance
    return ret;
  } else {
    // log('') translates to this
    // Strings are immutable so we can do this.
    return kEmptyString;
  }
}

LineReader* gStdin;

LineReader* open(Str* path) {
  StackRoots _roots({&path});

  // TODO: Don't use C I/O; use POSIX I/O!
  FILE* f = fopen(path->data_, "r");

  if (f == nullptr) {
    throw Alloc<IOError>(errno);
  }
  return Alloc<CFileLineReader>(f);
}

Str* CFileLineReader::readline() {
  char* line = nullptr;
  size_t allocated_size = 0;  // unused

  // Reset errno because we turn the EOF error into empty string (like Python).
  errno = 0;
  ssize_t len = getline(&line, &allocated_size, f_);
  if (len < 0) {
    if (errno != 0) {  // Unexpected error
      log("getline() error: %s", strerror(errno));
      throw Alloc<IOError>(errno);
    }
    // Expected EOF
    return kEmptyString;
  }

  // TODO: Fix the leak here.
  // Note: getline() NUL terminates the buffer
  return ::StrFromC(line, len);
}

// Problem: most Str methods like index() and slice() COPY so they have a
// NUL terminator.
// log("%s") falls back on sprintf, so it expects a NUL terminator.
// It would be easier for us to just share.
Str* BufLineReader::readline() {
  auto self = this;
  Str* line = nullptr;
  StackRoots _roots({&self, &line});

  int buf_len = len(s_);
  if (pos_ == buf_len) {
    return kEmptyString;
  }

  int orig_pos = pos_;
  const char* p = strchr(s_->data_ + pos_, '\n');
  // log("pos_ = %s", pos_);
  int line_len;
  if (p) {
    int new_pos = p - self->s_->data_;
    line_len = new_pos - pos_ + 1;  // past newline char
    pos_ = new_pos + 1;
  } else {  // leftover line
    line_len = buf_len - pos_;
    pos_ = buf_len;
  }

  line = AllocStr(line_len);
  memcpy(line->data_, self->s_->data_ + orig_pos, line_len);
  assert(line->data_[line_len] == '\0');
  return line;
}

Writer* gStdout;
Writer* gStderr;

void BufWriter::write(Str* s) {
  int orig_len = len_;
  int n = len(s);
  len_ += n;

  // BUG: This is quadratic!

  // TODO:
  //
  // - add capacity_, and double it?  start at 32 bytes -> 64 -> 128
  //   - only realloc by doublings?
  // - or change this to append to a list?  and then getvalue() does a join()
  // on it?
  // - DEALLOCATE.  gc_mylib doesn't leak!

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

void BufWriter::format_o(int i) {
  NotImplemented();
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

void CFileWriter::write(Str* s) {
  // note: throwing away the return value
  fwrite(s->data_, sizeof(char), len(s), f_);
}

void CFileWriter::flush() {
  ::fflush(f_);
}

bool CFileWriter::isatty() {
  return ::isatty(fileno(f_));
}

}  // namespace mylib
