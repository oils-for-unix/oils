// gc_mylib.h - corresponds to mycpp/mylib.py

#ifndef MYCPP_GC_MYLIB_H
#define MYCPP_GC_MYLIB_H

#include <limits.h>  // CHAR_BIT

#include "mycpp/gc_alloc.h"  // gHeap
#include "mycpp/gc_dict.h"   // kDeletedEntry
#include "mycpp/gc_tuple.h"

template <class K, class V>
class Dict;

// https://stackoverflow.com/questions/3919995/determining-sprintf-buffer-size-whats-the-standard/11092994#11092994
// Notes:
// - Python 2.7's intobject.c has an erroneous +6
// - This is 13, but len('-2147483648') is 11, which means we only need 12?
// - This formula is valid for octal(), because 2^(3 bits) = 8

const int kIntBufSize = CHAR_BIT * sizeof(int) / 3 + 3;

namespace mylib {

void ProcessInit();

// Wrappers around our C++ APIs

inline void MaybeCollect() {
  gHeap.MaybeCollect();
}

// Used by generated _build/cpp/osh_eval.cc
inline Str* StrFromC(const char* s) {
  return ::StrFromC(s);
}

const int kStdout = 1;
const int kStderr = 2;

void writeln(Str* s, int fd = kStdout);

Tuple2<Str*, Str*> split_once(Str* s, Str* delim);

template <typename K, typename V>
void dict_erase(Dict<K, V>* haystack, K needle) {
  int pos = haystack->position_of_key(needle);
  if (pos == -1) {
    return;
  }
  haystack->entry_->items_[pos] = kDeletedEntry;
  // Zero out for GC.  These could be nullptr or 0
  haystack->keys_->items_[pos] = 0;
  haystack->values_->items_[pos] = 0;
  haystack->len_--;
}

// NOTE: Can use OverAllocatedStr for all of these, rather than copying

inline Str* hex_lower(int i) {
  char buf[kIntBufSize];
  int len = snprintf(buf, kIntBufSize, "%x", i);
  return ::StrFromC(buf, len);
}

inline Str* hex_upper(int i) {
  char buf[kIntBufSize];
  int len = snprintf(buf, kIntBufSize, "%X", i);
  return ::StrFromC(buf, len);
}

inline Str* octal(int i) {
  char buf[kIntBufSize];
  int len = snprintf(buf, kIntBufSize, "%o", i);
  return ::StrFromC(buf, len);
}

class LineReader {
 public:
  // Abstract type with no fields: unknown size
  LineReader() : GC_CLASS_FIXED(header_, kZeroMask, kNoObjLen) {
  }
  virtual Str* readline() = 0;
  virtual bool isatty() = 0;
  virtual void close() = 0;

  GC_OBJ(header_);
};

class BufLineReader : public LineReader {
 public:
  explicit BufLineReader(Str* s) : LineReader(), s_(s), pos_(0) {
    FIELD_MASK(header_) |= BufLineReader::field_mask();
  }
  virtual Str* readline();
  virtual bool isatty() {
    return false;
  }
  virtual void close() {
  }

  Str* s_;
  int pos_;

  static constexpr unsigned field_mask() {
    return maskbit_v(offsetof(BufLineReader, s_));
  }

  DISALLOW_COPY_AND_ASSIGN(BufLineReader)
};

// Wrap a FILE*
class CFileLineReader : public LineReader {
 public:
  explicit CFileLineReader(FILE* f) : LineReader(), f_(f) {
    // not mutating field_mask because FILE* isn't a GC object
  }
  virtual Str* readline();
  virtual bool isatty();
  void close() {
    fclose(f_);
  }

 private:
  FILE* f_;

  DISALLOW_COPY_AND_ASSIGN(CFileLineReader)
};

extern LineReader* gStdin;

inline LineReader* Stdin() {
  if (gStdin == nullptr) {
    gStdin = Alloc<CFileLineReader>(stdin);
  }
  return gStdin;
}

LineReader* open(Str* path);

class Writer {
 public:
  // subclasses mutate the mask (and can set obj_len length for Cheney)
  Writer() : GC_CLASS_FIXED(header_, kZeroMask, kNoObjLen) {
  }
  virtual void write(Str* s) = 0;
  virtual void flush() = 0;
  virtual bool isatty() = 0;

  GC_OBJ(header_);
};

class MutableStr;

class BufWriter : public Writer {
 public:
  BufWriter() : Writer(), str_(nullptr), len_(0) {
    FIELD_MASK(header_) |= field_mask();
  }
  void write(Str* s) override;
  void flush() override {
  }
  bool isatty() override {
    return false;
  }
  // For cStringIO API
  Str* getvalue();

 private:
  void EnsureCapacity(int n);

  void Extend(Str* s);
  char* data();
  char* end();
  int capacity();

  MutableStr* str_;
  int len_;
  bool is_valid_ = true;  // It becomes invalid after getvalue() is called

  static constexpr unsigned field_mask() {
    // maskvit_v() because BufWriter has virtual methods
    return maskbit_v(offsetof(BufWriter, str_));
  }
};

// Wrap a FILE*
class CFileWriter : public Writer {
 public:
  explicit CFileWriter(FILE* f) : Writer(), f_(f) {
    // not mutating field_mask because FILE* is not a managed pointer
  }
  void write(Str* s) override;
  void flush() override;
  bool isatty() override;

 private:
  FILE* f_;

  DISALLOW_COPY_AND_ASSIGN(CFileWriter)
};

extern Writer* gStdout;

inline Writer* Stdout() {
  if (gStdout == nullptr) {
    gStdout = Alloc<CFileWriter>(stdout);
    gHeap.RootGlobalVar(gStdout);
  }
  return gStdout;
}

extern Writer* gStderr;

inline Writer* Stderr() {
  if (gStderr == nullptr) {
    gStderr = Alloc<CFileWriter>(stderr);
    gHeap.RootGlobalVar(gStderr);
  }
  return gStderr;
}

}  // namespace mylib

#endif  // MYCPP_GC_MYLIB_H
