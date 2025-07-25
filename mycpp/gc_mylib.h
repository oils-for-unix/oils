// gc_mylib.h - corresponds to mycpp/mylib.py

#ifndef MYCPP_GC_MYLIB_H
#define MYCPP_GC_MYLIB_H

#include "mycpp/gc_alloc.h"  // gHeap
#include "mycpp/gc_dict.h"   // for dict_erase()
#include "mycpp/gc_mops.h"
#include "mycpp/gc_tuple.h"

template <class K, class V>
class Dict;

namespace mylib {

bool isinf_(double f);
bool isnan_(double f);

void InitCppOnly();

// Wrappers around our C++ APIs

inline void MaybeCollect() {
  gHeap.MaybeCollect();
}

inline void PrintGcStats() {
  gHeap.PrintShortStats();  // print to stderr
}

void print_stderr(BigStr* s);

inline int ByteAt(BigStr* s, int i) {
  DCHECK(0 <= i);
  DCHECK(i <= len(s));

  return static_cast<unsigned char>(s->data_[i]);
}

inline int ByteEquals(int byte, BigStr* ch) {
  DCHECK(0 <= byte);
  DCHECK(byte < 256);

  DCHECK(len(ch) == 1);

  return byte == static_cast<unsigned char>(ch->data_[0]);
}

inline int ByteInSet(int byte, BigStr* byte_set) {
  DCHECK(0 <= byte);
  DCHECK(byte < 256);

  int n = len(byte_set);
  for (int i = 0; i < n; ++i) {
    int b = static_cast<unsigned char>(byte_set->data_[i]);
    if (byte == b) {
      return true;
    }
  }
  return false;
}

BigStr* JoinBytes(List<int>* byte_list);

void BigIntSort(List<mops::BigInt>* keys);

// const int kStdout = 1;
// const int kStderr = 2;

// void writeln(BigStr* s, int fd = kStdout);

Tuple2<BigStr*, BigStr*> split_once(BigStr* s, BigStr* delim);

template <typename K, typename V>
void dict_erase(Dict<K, V>* haystack, K needle) {
  DCHECK(haystack->obj_header().heap_tag != HeapTag::Global);

  int pos = haystack->hash_and_probe(needle);
  if (pos == kTooSmall) {
    return;
  }
  DCHECK(pos >= 0);
  int kv_index = haystack->index_->items_[pos];
  if (kv_index < 0) {
    return;
  }

  int last_kv_index = haystack->len_ - 1;
  DCHECK(kv_index <= last_kv_index);

  // Swap the target entry with the most recently inserted one before removing
  // it. This has two benefits.
  //   (1) It keeps the entry arrays compact. All valid entries occupy a
  //       contiguous region in memory.
  //   (2) It prevents holes in the entry arrays. This makes iterating over
  //       entries (e.g. in keys() or DictIter()) trivial and doesn't require
  //       any extra validity state (like a bitset of unusable slots). This is
  //       important because keys and values wont't always be pointers, so we
  //       can't rely on NULL checks for validity. We also can't wrap the slab
  //       entry types in some other type without modifying the garbage
  //       collector to trace through unmanaged types (or paying the extra
  //       allocations for the outer type).
  if (kv_index != last_kv_index) {
    K last_key = haystack->keys_->items_[last_kv_index];
    V last_val = haystack->values_->items_[last_kv_index];
    int last_pos = haystack->hash_and_probe(last_key);
    DCHECK(last_pos != kNotFound);
    haystack->keys_->items_[kv_index] = last_key;
    haystack->values_->items_[kv_index] = last_val;
    haystack->index_->items_[last_pos] = kv_index;
  }

  // Zero out for GC.  These could be nullptr or 0
  haystack->keys_->items_[last_kv_index] = 0;
  haystack->values_->items_[last_kv_index] = 0;
  haystack->index_->items_[pos] = kDeletedEntry;
  haystack->len_--;
  DCHECK(haystack->len_ < haystack->capacity_);
}

inline BigStr* hex_lower(int i) {
  // Note: Could also use OverAllocatedStr, but most strings are small?
  char buf[kIntBufSize];
  int len = snprintf(buf, kIntBufSize, "%x", i);
  return ::StrFromC(buf, len);
}

// Abstract type: Union of LineReader and Writer
class File {
 public:
  File() {
  }
  // Writer
  virtual void write(BigStr* s) = 0;
  virtual void flush() = 0;

  // Reader
  virtual BigStr* readline() = 0;

  // Both
  virtual bool isatty() = 0;
  virtual void close() = 0;

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(File));
  }

  static constexpr uint32_t field_mask() {
    return kZeroMask;
  }
};

// Wrap a FILE* for read and write
class CFile : public File {
 public:
  explicit CFile(FILE* f) : File(), f_(f) {
  }
  // Writer
  void write(BigStr* s) override;
  void flush() override;

  // Reader
  BigStr* readline() override;

  // Both
  bool isatty() override;
  void close() override;

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(CFile));
  }

  static constexpr uint32_t field_mask() {
    // not mutating field_mask because FILE* isn't a GC object
    return File::field_mask();
  }

 private:
  FILE* f_;

  DISALLOW_COPY_AND_ASSIGN(CFile)
};

// Abstract File we can only read from.
// TODO: can we get rid of DCHECK() and reinterpret_cast?
class LineReader : public File {
 public:
  LineReader() : File() {
  }
  void write(BigStr* s) override {
    CHECK(false);  // should not happen
  }
  void flush() override {
    CHECK(false);  // should not happen
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(LineReader));
  }

  static constexpr uint32_t field_mask() {
    return kZeroMask;
  }
};

class BufLineReader : public LineReader {
 public:
  explicit BufLineReader(BigStr* s) : LineReader(), s_(s), pos_(0) {
  }
  virtual BigStr* readline();
  virtual bool isatty() {
    return false;
  }
  virtual void close() {
  }

  BigStr* s_;
  int pos_;

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(LineReader));
  }

  static constexpr uint32_t field_mask() {
    return LineReader::field_mask() | maskbit(offsetof(BufLineReader, s_));
  }

  DISALLOW_COPY_AND_ASSIGN(BufLineReader)
};

extern LineReader* gStdin;

inline LineReader* Stdin() {
  if (gStdin == nullptr) {
    gStdin = reinterpret_cast<LineReader*>(Alloc<CFile>(stdin));
  }
  return gStdin;
}

LineReader* open(BigStr* path);

// Abstract File we can only write to.
// TODO: can we get rid of DCHECK() and reinterpret_cast?
class Writer : public File {
 public:
  Writer() : File() {
  }
  BigStr* readline() override {
    CHECK(false);  // should not happen
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(Writer));
  }

  static constexpr uint32_t field_mask() {
    return kZeroMask;
  }
};

class MutableStr;

class BufWriter : public Writer {
 public:
  BufWriter() : Writer(), str_(nullptr), len_(0) {
  }
  void write(BigStr* s) override;
  void write_spaces(int n);
  void clear() {  // Reuse this instance
    str_ = nullptr;
    len_ = 0;
    is_valid_ = true;
  }
  void close() override {
  }
  void flush() override {
  }
  bool isatty() override {
    return false;
  }
  BigStr* getvalue();  // part of cStringIO API

  //
  // Low Level API for C++ usage only
  //

  // Convenient API that avoids BigStr*
  void WriteConst(const char* c_string);

  // Potentially resizes the buffer.
  void EnsureMoreSpace(int n);
  // After EnsureMoreSpace(42), you can write 42 more bytes safely.
  //
  // Note that if you call EnsureMoreSpace(42), write 5 byte, and then
  // EnsureMoreSpace(42) again, the amount of additional space reserved is 47.

  // (Similar to vector::reserve(n), but it takes an integer to ADD to the
  // capacity.)

  uint8_t* LengthPointer();    // start + length
  uint8_t* CapacityPointer();  // start + capacity
  void SetLengthFrom(uint8_t* length_ptr);

  int Length() {
    return len_;
  }

  // Rewind to earlier position, future writes start there
  void Truncate(int length);

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(BufWriter));
  }

  static constexpr unsigned field_mask() {
    // maskvit_v() because BufWriter has virtual methods
    return Writer::field_mask() | maskbit(offsetof(BufWriter, str_));
  }

 private:
  void WriteRaw(char* s, int n);

  MutableStr* str_;  // getvalue() turns this directly into Str*, no copying
  int len_;          // how many bytes have been written so far
  bool is_valid_ = true;  // It becomes invalid after getvalue() is called
};

extern Writer* gStdout;

inline Writer* Stdout() {
  if (gStdout == nullptr) {
    gStdout = reinterpret_cast<Writer*>(Alloc<CFile>(stdout));
    gHeap.RootGlobalVar(gStdout);
  }
  return gStdout;
}

extern Writer* gStderr;

inline Writer* Stderr() {
  if (gStderr == nullptr) {
    gStderr = reinterpret_cast<Writer*>(Alloc<CFile>(stderr));
    gHeap.RootGlobalVar(gStderr);
  }
  return gStderr;
}

class UniqueObjects {
  // Can't be expressed in typed Python because we don't have uint64_t for
  // addresses

 public:
  UniqueObjects() {
  }
  void Add(void* obj) {
  }
  int Get(void* obj) {
    return -1;
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(UniqueObjects));
  }

  // SPECIAL CASE? We should never have a unique reference to an object?  So
  // don't bother tracing
  static constexpr uint32_t field_mask() {
    return kZeroMask;
  }

 private:
  // address -> small integer ID
  Dict<void*, int> addresses_;
};

}  // namespace mylib

#endif  // MYCPP_GC_MYLIB_H
