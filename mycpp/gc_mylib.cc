#include "mycpp/gc_mylib.h"

#include <errno.h>
#include <stdio.h>
#include <unistd.h>  // isatty

namespace mylib {

void InitCppOnly() {
  // We don't seem need this now that we have ctx_FlushStdout().
  // setvbuf(stdout, 0, _IONBF, 0);

  // Arbitrary threshold of 50K objects based on eyeballing
  // benchmarks/osh-runtime 10K or 100K aren't too bad either.
  gHeap.Init(50000);
}

void print_stderr(Str* s) {
  fputs(s->data_, stderr);  // prints until first NUL
  fputc('\n', stderr);
}

#if 0
void writeln(Str* s, int fd) {
  // TODO: handle errors and write in a loop, like posix::write().  If possible,
  // use posix::write directly, but that introduces some dependency problems.

  if (write(fd, s->data_, len(s)) < 0) {
    assert(0);
  }
  if (write(fd, "\n", 1) < 0) {
    assert(0);
  }
}
#endif

class MutableStr : public Str {};

MutableStr* NewMutableStr(int cap) {
  // In order for everything to work, MutableStr must be identical in layout to
  // Str. One easy way to achieve this is for MutableStr to have no members and
  // to inherit from Str.
  static_assert(sizeof(MutableStr) == sizeof(Str),
                "Str and MutableStr must have same size");
  return reinterpret_cast<MutableStr*>(NewStr(cap));
}

Tuple2<Str*, Str*> split_once(Str* s, Str* delim) {
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
    // Allocate together to avoid 's' moving in between
    s1 = NewStr(len1);
    s2 = NewStr(len2);

    memcpy(s1->data_, s->data_, len1);
    memcpy(s2->data_, s->data_ + len1 + 1, len2);

    return Tuple2<Str*, Str*>(s1, s2);
  } else {
    return Tuple2<Str*, Str*>(s, nullptr);
  }
}

LineReader* gStdin;

LineReader* open(Str* path) {
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
    // man page says the buffer should be freed even if getline fails
    free(line);
    if (errno != 0) {  // Unexpected error
      log("getline() error: %s", strerror(errno));
      throw Alloc<IOError>(errno);
    }
    // Expected EOF
    return kEmptyString;
  }

  // Note: getline() NUL terminates the buffer
  Str* result = ::StrFromC(line, len);
  free(line);
  return result;
}

bool CFileLineReader::isatty() {
  return ::isatty(fileno(f_));
}

// Problem: most Str methods like index() and slice() COPY so they have a
// NUL terminator.
// log("%s") falls back on sprintf, so it expects a NUL terminator.
// It would be easier for us to just share.
Str* BufLineReader::readline() {
  Str* line = nullptr;

  int str_len = len(s_);
  if (pos_ == str_len) {
    return kEmptyString;
  }

  int orig_pos = pos_;
  const char* p = strchr(s_->data_ + pos_, '\n');
  // log("pos_ = %s", pos_);
  int line_len;
  if (p) {
    int new_pos = p - s_->data_;
    line_len = new_pos - pos_ + 1;  // past newline char
    pos_ = new_pos + 1;
  } else {             // leftover line
    if (pos_ == 0) {   // The string has no newlines at all -- just return it
      pos_ = str_len;  // advance to the end
      return s_;
    } else {
      line_len = str_len - pos_;
      pos_ = str_len;  // advance to the end
    }
  }

  line = NewStr(line_len);
  memcpy(line->data_, s_->data_ + orig_pos, line_len);
  assert(line->data_[line_len] == '\0');
  return line;
}

Writer* gStdout;
Writer* gStderr;

//
// CFileWriter
//

void CFileWriter::write(Str* s) {
  // note: throwing away the return value
  fwrite(s->data_, sizeof(char), len(s), f_);
}

void CFileWriter::flush() {
  ::fflush(f_);
}

bool CFileWriter::isatty() {
  return ::isatty(::fileno(f_));
}

//
// BufWriter
//

char* BufWriter::data() {
  assert(str_);
  return str_->data_;
}

char* BufWriter::end() {
  assert(str_);
  return str_->data_ + len_;
}

int BufWriter::capacity() {
  return str_ ? len(str_) : 0;
}

void BufWriter::Extend(Str* s) {
  const int n = len(s);

  assert(capacity() >= len_ + n);

  memcpy(end(), s->data_, n);
  len_ += n;
  data()[len_] = '\0';
}

// TODO: realloc() to new capacity instead of creating NewBuf()
void BufWriter::EnsureCapacity(int cap) {
  assert(capacity() >= len_);

  if (capacity() < cap) {
    auto* s = NewMutableStr(std::max(capacity() * 2, cap));
    memcpy(s->data_, str_->data_, len_);
    s->data_[len_] = '\0';
    str_ = s;
  }
}

void BufWriter::write(Str* s) {
  assert(is_valid_);  // Can't write() after getvalue()

  int n = len(s);

  // write('') is a no-op, so don't create Buf if we don't need to
  if (n == 0) {
    return;
  }

  if (str_ == nullptr) {
    // TODO: we could make the default capacity big enough for a line, e.g. 128
    // capacity: 128 -> 256 -> 512
    str_ = NewMutableStr(n);
  } else {
    EnsureCapacity(len_ + n);
  }

  // Append the contents to the buffer
  Extend(s);
}

Str* BufWriter::getvalue() {
  assert(is_valid_);  // Check for two INVALID getvalue() in a row
  is_valid_ = false;

  if (str_ == nullptr) {  // if no write() methods are called, the result is ""
    return kEmptyString;
  } else {
    Str* s = str_;
    s->MaybeShrink(len_);
    str_ = nullptr;
    len_ = -1;
    return s;
  }
}

}  // namespace mylib
