// mylib.cc

#include "mylib.h"

#include <assert.h>
#include <stdarg.h>  // va_list, etc.
#include <stdio.h>
#include <unistd.h>  // isatty

#include <exception>  // std::exception

Str* kEmptyString = new Str("", 0);

void print(Str* s) {
  printf("%s\n", s->data_);
}

void println_stderr(Str* s) {
  fputs(s->data_, stderr);
  fputs("\n", stderr);
}

void log(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vfprintf(stderr, fmt, args);
  va_end(args);
  fprintf(stderr, "\n");
}

// NOTE:
// - there's a third 'count' argument we're not using.
// - len(old) == 1 is a very common case we could make more efficient
//   - CPython has like 10 special cases for this!  It detects if len(old) ==
//     len(new) as well.
// - we're not handling internal NULs (because of strstr())
Str* Str::replace(Str* old, Str* new_str) {
  //log("replacing %s with %s", old_data, new_str->data_);

  const char* old_data = old->data_;
  const char* last_possible = data_ + len_ - old->len_;

  const char* p_this = data_;  // advances through 'this'

  // First pass to calculate the new length
  int replace_count = 0;
  while (p_this < last_possible) {
    const char* next = strstr(p_this, old_data);
    if (next == NULL) {
      break;
    }
    replace_count++;
    p_this = next + old->len_;  // skip past
  }

  //log("done %d", replace_count);

  if (replace_count == 0) {
    return this;  // Reuse the string if there were no replacements
  }

  int len = this->len_ - (replace_count * old->len_)
                       + (replace_count * new_str->len_);

  char* result = static_cast<char*>(malloc(len + 1));  // +1 for NUL

  const char* new_data = new_str->data_;
  const size_t new_len = new_str->len_;

  // Second pass to copy into new 'result'
  p_this = data_;
  char* p_result = result;  // advances through 'result'

  for (int i = 0; i < replace_count; ++i) {
    const char* next = strstr(p_this, old_data);
    assert(p_this != NULL);
    size_t n = next - p_this;

    memcpy(p_result, p_this, n);  // Copy from 'this'
    p_result += n;

    memcpy(p_result, new_data, new_len);  // Copy from new_str
    p_result += new_len;

    p_this = next + old->len_;
  }
  memcpy(p_result, p_this, data_ + len_ - p_this);  // Copy the rest of 'this'
  result[len] = '\0';  // NUL terminate

  return new Str(result);
}

Str* Str::join(List<Str*>* items) {
  int len = 0;
  const std::vector<Str*>& v = items->v_;
  for (int i = 0; i < v.size(); ++i) {
    len += v[i]->len_;
  }
  // add length of all the separators
  len += len_ * (v.size() - 1);

  //log("len: %d", len);
  //log("v.size(): %d", v.size());

  char* result = static_cast<char*>(malloc(len+1));
  char* p_result = result;  // advances through

  for (int i = 0; i < v.size(); ++i) {
    //log("i %d", i);
    if (i != 0 && len_) {  // optimize common case of ''.join()
      memcpy(p_result, data_, len_);  // copy the separator
      p_result += len_;
      //log("len_ %d", len_);
    }

    int n = v[i]->len_;
    //log("n: %d", n);
    memcpy(p_result, v[i]->data_, n);  // copy the list item
    p_result += n;
  }

  result[len] = '\0';  // NUL terminator

  return new Str(result, len);
}

// Get a string with one character
Str* StrIter::Value() {
  char* buf = static_cast<char*>(malloc(2));
  buf[0] = s_->data_[i_];
  buf[1] = '\0';
  return new Str(buf, 1);
}

namespace mylib {

//
// LineReader
//

Str* kEmptyString = new Str("");

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
  //log("pos_ = %s", pos_);
  int len;
  if (new_pos) {
    len = new_pos - pos_ + 1;  // past newline char
    pos_ = new_pos + 1;
  } else {  // leftover line
    len = end - pos_;
    pos_ = end;
  }

  char* result = static_cast<char*>(malloc(len+1));
  memcpy(result, orig_pos, len);  // copy the list item
  result[len] = '\0';
  Str* line = new Str(result, len);

  // Easier way:
  //Str* line = new Str(pos_, new_pos - pos_);
  return line;
}

//
// Writer
//

Writer* gStdout;

void BufWriter::write(Str* s) {
  int orig_len = len_;
  len_ += s->len_;
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

void BufWriter::format_r(Str* s) {
  assert(0);
}

//void BufWriter::format_s(const char* s) {
//  this->write_const(s, strlen(s));
//}

void CFileWriter::write(Str* s) {
  // note: throwing away the return value
  fwrite(s->data_, s->len_, 1, f_);
}

bool CFileWriter::isatty() {
  return ::isatty(fileno(f_));
}

}  // namespace mylib

//
// Free functions
//

Str* str_concat(Str* a, Str* b) {
  int new_len = a->len_ + b->len_;
  char* buf = static_cast<char*>(malloc(new_len + 1));

  int len_a = a->len_;
  memcpy(buf, a->data_, len_a);
  memcpy(buf + len_a, b->data_, b->len_);
  buf[new_len] = '\0';

  return new Str(buf, new_len);
}

Str* str_repeat(Str* s, int times) {
  int len = s->len_;
  int new_len = len * times;
  char* data_ = static_cast<char*>(malloc(new_len + 1));

  char* dest = data_;
  for (int i = 0; i < times; i++) {
    memcpy(dest, s->data_, len);
    dest += len;
  }
  data_[new_len] = '\0';
  return new Str(data_, new_len);
}

// Helper for str_to_int() that doesn't use exceptions.
// Like atoi(), but with better error checking.
bool _str_to_int(Str* s, int* result) {
  if (s->len_ == 0) {
    return false;  // special case for empty string
  }

  char* p;  // mutated by strtol
  *result = strtol(s->data_, &p, 10);  // base 10

  // Return true if it consumed ALL characters.
  const char* end = s->data_ + s->len_;
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
int str_to_int(Str* s) {
  int i;
  if (_str_to_int(s, &i)) {
    return i;
  } else {
    throw std::exception();  // TODO: should be ValueError
  }
}

//
// Formatter
//

mylib::BufWriter gBuf;

