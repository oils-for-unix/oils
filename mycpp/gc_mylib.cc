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

void print_stderr(BigStr* s) {
  fputs(s->data_, stderr);  // prints until first NUL
  fputc('\n', stderr);
}

#if 0
void writeln(BigStr* s, int fd) {
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

BigStr* JoinBytes(List<int>* byte_list) {
  int n = len(byte_list);
  BigStr* result = NewStr(n);
  for (int i = 0; i < n; ++i) {
    result->data_[i] = byte_list->at(i);
  }
  return result;
}

class MutableStr : public BigStr {};

MutableStr* NewMutableStr(int n) {
  // In order for everything to work, MutableStr must be identical in layout to
  // BigStr. One easy way to achieve this is for MutableStr to have no members
  // and to inherit from BigStr.
  static_assert(sizeof(MutableStr) == sizeof(BigStr),
                "BigStr and MutableStr must have same size");
  return reinterpret_cast<MutableStr*>(NewStr(n));
}

Tuple2<BigStr*, BigStr*> split_once(BigStr* s, BigStr* delim) {
  DCHECK(len(delim) == 1);

  const char* start = s->data_;  // note: this pointer may move
  char c = delim->data_[0];
  int length = len(s);

  const char* p = static_cast<const char*>(memchr(start, c, length));

  if (p) {
    int len1 = p - start;
    int len2 = length - len1 - 1;  // -1 for delim

    BigStr* s1 = nullptr;
    BigStr* s2 = nullptr;
    // Allocate together to avoid 's' moving in between
    s1 = NewStr(len1);
    s2 = NewStr(len2);

    memcpy(s1->data_, s->data_, len1);
    memcpy(s2->data_, s->data_ + len1 + 1, len2);

    return Tuple2<BigStr*, BigStr*>(s1, s2);
  } else {
    return Tuple2<BigStr*, BigStr*>(s, nullptr);
  }
}

LineReader* gStdin;

LineReader* open(BigStr* path) {
  // TODO: Don't use C I/O; use POSIX I/O!
  FILE* f = fopen(path->data_, "r");
  if (f == nullptr) {
    throw Alloc<IOError>(errno);
  }

  return reinterpret_cast<LineReader*>(Alloc<CFile>(f));
}

BigStr* CFile::readline() {
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
    return kEmptyString;  // EOF indicated by by empty string, like Python
  }

  // Note: getline() NUL-terminates the buffer
  BigStr* result = ::StrFromC(line, len);
  free(line);
  return result;
}

bool CFile::isatty() {
  return ::isatty(fileno(f_));
}

// Problem: most BigStr methods like index() and slice() COPY so they have a
// NUL terminator.
// log("%s") falls back on sprintf, so it expects a NUL terminator.
// It would be easier for us to just share.
BigStr* BufLineReader::readline() {
  BigStr* line = nullptr;

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
  DCHECK(line->data_[line_len] == '\0');
  return line;
}

Writer* gStdout;
Writer* gStderr;

//
// CFileWriter
//

void CFile::write(BigStr* s) {
  // Writes can be short!
  int n = len(s);
  int num_written = ::fwrite(s->data_, sizeof(char), n, f_);
  // Similar to CPython fileobject.c
  if (num_written != n) {
    throw Alloc<IOError>(errno);
  }
}

void CFile::flush() {
  if (::fflush(f_) != 0) {
    throw Alloc<IOError>(errno);
  }
}

void CFile::close() {
  if (::fclose(f_) != 0) {
    throw Alloc<IOError>(errno);
  }
}

//
// BufWriter
//

void BufWriter::EnsureMoreSpace(int n) {
  if (str_ == nullptr) {
    // TODO: we could make the default capacity big enough for a line, e.g. 128
    // capacity: 128 -> 256 -> 512
    str_ = NewMutableStr(n);
    return;
  }

  int current_cap = len(str_);
  DCHECK(current_cap >= len_);

  int new_cap = len_ + n;

  if (current_cap < new_cap) {
    auto* s = NewMutableStr(std::max(current_cap * 2, new_cap));
    memcpy(s->data_, str_->data_, len_);
    s->data_[len_] = '\0';
    str_ = s;
  }
}

uint8_t* BufWriter::LengthPointer() {
  // start + len
  return reinterpret_cast<uint8_t*>(str_->data_) + len_;
}

uint8_t* BufWriter::CapacityPointer() {
  // start + capacity
  return reinterpret_cast<uint8_t*>(str_->data_) + str_->len_;
}

void BufWriter::SetLengthFrom(uint8_t* length_ptr) {
  uint8_t* begin = reinterpret_cast<uint8_t*>(str_->data_);
  DCHECK(length_ptr >= begin);  // we should have written some data

  // Set the length, e.g. so we know where to resume writing from
  len_ = length_ptr - begin;
  // printf("SET LEN to %d\n", len_);
}

void BufWriter::Truncate(int length) {
  len_ = length;
}

void BufWriter::WriteRaw(char* s, int n) {
  DCHECK(is_valid_);  // Can't write() after getvalue()

  // write('') is a no-op, so don't create Buf if we don't need to
  if (n == 0) {
    return;
  }

  EnsureMoreSpace(n);

  // Append the contents to the buffer
  memcpy(str_->data_ + len_, s, n);
  len_ += n;
  str_->data_[len_] = '\0';
}

void BufWriter::WriteConst(const char* c_string) {
  // meant for short strings like '"'
  WriteRaw(const_cast<char*>(c_string), strlen(c_string));
}

void BufWriter::write(BigStr* s) {
  WriteRaw(s->data_, len(s));
}

void BufWriter::write_spaces(int n) {
  if (n == 0) {
    return;
  }

  EnsureMoreSpace(n);

  char* dest = str_->data_ + len_;
  for (int i = 0; i < n; ++i) {
    dest[i] = ' ';
  }
  len_ += n;
  str_->data_[len_] = '\0';
}

BigStr* BufWriter::getvalue() {
  DCHECK(is_valid_);  // Check for two INVALID getvalue() in a row
  is_valid_ = false;

  if (str_ == nullptr) {  // if no write() methods are called, the result is ""
    return kEmptyString;
  } else {
    BigStr* s = str_;
    s->MaybeShrink(len_);
    str_ = nullptr;
    len_ = -1;
    return s;
  }
}

}  // namespace mylib
