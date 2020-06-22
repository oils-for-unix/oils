// mylib.h

#ifndef MYLIB_H
#define MYLIB_H

#include <assert.h>
#include <ctype.h>   // isalpha(), isdigit()
#include <stdlib.h>  // malloc
#include <string.h>  // strlen
// https://stackoverflow.com/questions/3882346/forward-declare-file
#include <climits>  // CHAR_BIT
#include <cstdint>
#include <cstdio>  // FILE*
#include <initializer_list>
#include <unordered_map>
#include <vector>

#ifdef DUMB_ALLOC
#include "dumb_alloc.h"
#define malloc dumb_malloc
#define free dumb_free
#endif

// To reduce code size

#define DISALLOW_COPY_AND_ASSIGN(TypeName) \
  TypeName(TypeName&) = delete;            \
  void operator=(TypeName) = delete;

class Str;
template <class T>
class List;
template <class K, class V>
class Dict;

extern Str* kEmptyString;

// for hand-written code
void log(const char* fmt, ...);

void print(Str* s);

// log() generates code that writes this
void println_stderr(Str* s);

//
// TODO: Fill exceptions in
//

class IOError {};
class OSError {};

class IndexError {};
class ValueError {};
class KeyError {};

class EOFError {};

class NotImplementedError {
 public:
  NotImplementedError() {
  }
  explicit NotImplementedError(int i) {  // e.g. in expr_to_ast
  }
  explicit NotImplementedError(const char* s) {
  }
  explicit NotImplementedError(Str* s) {
  }
};

class AssertionError {
 public:
  AssertionError() {
  }
  explicit AssertionError(int i) {  // e.g. in expr_to_ast
  }
  explicit AssertionError(const char* s) {
  }
  explicit AssertionError(Str* s) {
  }
};

// Python's RuntimeError looks like this.  . libc::regex_match and other
// bindings raise it.
class RuntimeError {
 public:
  RuntimeError(Str* message) : message(message) {
  }
  Str* message;
};

//
// Data Types
//

// every ASDL type inherits from this, and provides tag() to
// static_cast<>(this->tag) to its own enum?

class Obj {
 public:
  // default constructor for multiple inheritance
  constexpr Obj() : tag(0) {
  }
  explicit Obj(uint16_t tag) : tag(tag) {
  }
  uint16_t tag;

  DISALLOW_COPY_AND_ASSIGN(Obj)
};

// TODO: Consider a couple extra fields:
// - lazy .str0() field on this immutable slice, rather than instantiating Str0
//   in every binding.
// - Cached hash code here.

class Str {
 public:
  explicit Str(const char* data) : data_(data) {
    len_ = strlen(data);
  }

  // constexpr so we can statically initialize Str s = {"foo", 3}
  constexpr Str(const char* data, int len) : data_(data), len_(len) {
  }

  // Important invariant: the buffer is of size len+1, so data[len] is OK to
  // access!  Not just data[len-1].  We use that to test if it's a C string.
  // note: "foo" and "foo\0" are both NUL-terminated.
  bool IsNulTerminated() {
    return data_[len_] == '\0';
  }

  // Get a string with one character
  Str* index(int i) {
    if (i < 0) {
      i = len_ + i;
    }
    char* buf = static_cast<char*>(malloc(2));
    buf[0] = data_[i];
    buf[1] = '\0';
    return new Str(buf, 1);
  }

  // s[begin:]
  Str* slice(int begin) {
    if (begin == 0) {
      return this;  // s[i:] where i == 0 is common in here docs
    }
    if (begin < 0) {
      begin = len_ + begin;
    }
    return slice(begin, len_);
  }
  // s[begin:end]
  Str* slice(int begin, int end) {
    if (begin < 0) {
      begin = len_ + begin;
    }
    if (end < 0) {
      end = len_ + end;
    }
    int new_len = end - begin;
    char* buf = static_cast<char*>(malloc(new_len + 1));
    memcpy(buf, data_ + begin, new_len);
    buf[new_len] = '\0';
    return new Str(buf, new_len);
  }

  // Helper for lstrip() and strip()
  int _strip_left_pos() {
    assert(len_ > 0);

    int i = 0;
    bool done = false;
    while (i < len_ && !done) {
      switch (data_[i]) {
      case ' ':
      case '\t':
      case '\r':
      case '\n':
        i++;
      default:
        done = true;
        break;
      }
    }
    return i;
  }

  // Helper for rstrip() and strip()
  int _strip_right_pos() {
    assert(len_ > 0);

    int last = len_ - 1;
    int i = last;
    bool done = false;
    while (i > 0 && !done) {
      switch (data_[i]) {
      case ' ':
      case '\t':
      case '\r':
      case '\n':
        i--;
      default:
        done = true;
        break;
      }
    }
    return i;
  }

  Str* strip() {
    if (len_ == 0) {
      return this;
    }
    int left_pos = _strip_left_pos();
    int right_pos = _strip_right_pos();

    if (left_pos == 0 && right_pos == len_ - 1) {
      return this;
    }

    // cstring-NOTE: This returns a SLICE, not a copy, unlike rstrip()
    // TODO: make them consistent.
    int len = right_pos - left_pos + 1;
    return new Str(data_ + left_pos, len);
  }

  // Used for CommandSub in osh/cmd_exec.py
  Str* rstrip(Str* chars) {
    assert(0);
  }

  Str* rstrip() {
    if (len_ == 0) {
      return this;
    }
    int right_pos = _strip_right_pos();
    if (right_pos == len_ - 1) {  // nothing stripped
      return this;
    }
    int new_len = right_pos + 1;
    char* buf = static_cast<char*>(malloc(new_len + 1));
    memcpy(buf, data_, new_len);
    buf[new_len] = '\0';
    return new Str(buf, new_len);
  }

  bool startswith(Str* s) {
    if (s->len_ >= len_) {
      return false;
    }
    return memcmp(data_, s->data_, s->len_) == 0;
  }
  bool endswith(Str* s) {
    if (s->len_ >= len_) {
      return false;
    }
    const char* start = data_ + len_ - s->len_;
    return memcmp(start, s->data_, s->len_) == 0;
  }
  bool isdigit() {
    if (len_ == 0) {
      return false;  // special case
    }
    for (int i = 0; i < len_; ++i) {
      if (!::isdigit(data_[i])) {
        return false;
      }
    }
    return true;
  }
  bool isalpha() {
    if (len_ == 0) {
      return false;  // special case
    }
    for (int i = 0; i < len_; ++i) {
      if (!::isalpha(data_[i])) {
        return false;
      }
    }
    return true;
  }
  // e.g. for osh/braces.py
  bool isupper() {
    if (len_ == 0) {
      return false;  // special case
    }
    for (int i = 0; i < len_; ++i) {
      if (!::isupper(data_[i])) {
        return false;
      }
    }
    return true;
  }

  List<Str*>* split(Str* sep);
  List<Str*>* splitlines(bool keep);
  Str* join(List<Str*>* items);

  Str* replace(Str* old, Str* new_str);

  int find(Str* needle) {
    assert(needle->len_ == 1);  // Oil's usage
    char c = needle->data_[0];
    for (int i = 0; i < len_; ++i) {
      if (data_[i] == c) {
        return i;
      }
    }
    return -1;
  }

  Str* upper() {
    assert(0);
  }

  Str* lower() {
    assert(0);
  }

  Str* ljust(int width, Str* fillchar) {
    assert(0);
  }

  Str* rjust(int width, Str* fillchar) {
    assert(0);
  }

  const char* data_;
  int len_;

  DISALLOW_COPY_AND_ASSIGN(Str)
};

// NOTE: This iterates over bytes.
class StrIter {
 public:
  explicit StrIter(Str* s) : s_(s), i_(0) {
  }
  void Next() {
    i_++;
  }
  bool Done() {
    return i_ >= s_->len_;
  }
  Str* Value();

 private:
  Str* s_;
  int i_;

  DISALLOW_COPY_AND_ASSIGN(StrIter)
};

// TODO: Rewrite without vector<>, so we don't depend on libstdc++.
template <class T>
class List {
 public:
  // Note: constexpr doesn't work because the std::vector destructor is
  // nontrivial
  constexpr List() : v_() {
    // Note: this seems to INCREASE the number of 'new' calls.  I guess because
    // many 'spids' lists aren't used?
    // v_.reserve(64);
  }

  // Used by list_repeat
  List(T item, int n) : v_(n, item) {
  }

  List(std::initializer_list<T> init) : v_() {
    for (T item : init) {
      v_.push_back(item);
    }
  }

  // a[-1] = 42 becomes a->set(-1, 42);
  void set(int index, T value) {
    if (index < 0) {
      index = v_.size() + index;
    }
    v_[index] = value;
  }

  T index(int i) const {
    if (i < 0) {
      // User code doesn't result in mylist[-1], but Oil's own code does
      int j = v_.size() + i;
      return v_.at(j);
    }
    return v_.at(i);  // checked version
  }

  // L[begin:]
  List* slice(int begin) {
    if (begin == 0) {
      return this;
    }
    if (begin < 0) {
      begin = v_.size() + begin;
    }

    List* result = new List();
    int len = v_.size();
    for (int i = begin; i < len; i++) {
      result->v_.push_back(v_[i]);
    }
    return result;
  }
  // L[begin:end]
  // TODO: Can this be optimized?
  List* slice(int begin, int end) {
    if (begin < 0) {
      begin = v_.size() + begin;
    }
    if (end < 0) {
      end = v_.size() + end;
    }

    List* result = new List();
    for (int i = begin; i < end; i++) {
      result->v_.push_back(v_[i]);
    }
    return result;
  }

  void append(T item) {
#ifdef SIZE_LOG
    // we can post process this format to find large lists
    // except when they're constants, but that's OK?
    printf("%p %zu\n", this, v_.size());
#endif

    v_.push_back(item);
  }

  void extend(List<T>* items) {
    // Note: C++ idioms would be v_.insert() or std::copy, but we're keeping it
    // simple.
    //
    // We could optimize this for the small cases Oil has?  I doubt it's a
    // bottleneck anywhere.
    int len = items->v_.size();
    for (int i = 0; i < len; ++i) {
      v_.push_back(items->v_[i]);
    }
  }

  // Reconsider?
  // https://stackoverflow.com/questions/12600330/pop-back-return-value
  T pop() {
    assert(!v_.empty());
    T result = v_.back();
    v_.pop_back();
    return result;
  }

  // Used in osh/word_parse.py to remove from front
  // TODO: Don't accept arbitrary index?
  T pop(int index) {
    if (v_.size() == 0) {
      // TODO: Handle this better?
      assert(0);
    }

    T result = v_.at(index);
    v_.erase(v_.begin() + index);
    return result;

    /*
    Implementation without std::vector
    assert(index == 0);
    for (int i = 1; i < v_.size(); ++i) {
      v_[i-1] = v_[i];
    }
    v_.pop_back();
    */
  }

  void clear() {
    v_.clear();
  }

  void sort() {
    assert(0);
  }

  // in osh/string_ops.py
  void reverse() {
    assert(0);
  }

  // private:
  std::vector<T> v_;  // ''.join accesses this directly
};

template <class T>
class ListIter {
 public:
  explicit ListIter(List<T>* L) : L_(L), i_(0) {
  }
  void Next() {
    i_++;
  }
  bool Done() {
    // "unsigned size_t was a mistake"
    return i_ >= static_cast<int>(L_->v_.size());
  }
  T Value() {
    return L_->v_[i_];
  }

 private:
  List<T>* L_;
  int i_;
};

// TODO: Does using pointers rather than indices make this more efficient?
template <class T>
class ReverseListIter {
 public:
  explicit ReverseListIter(List<T>* L) : L_(L), i_(L_->v_.size() - 1) {
  }
  void Next() {
    i_--;
  }
  bool Done() {
    return i_ < 0;
  }
  T Value() {
    return L_->v_[i_];
  }

 private:
  List<T>* L_;
  int i_;
};

template <class K, class V>
class DictIter {
 public:
  explicit DictIter(Dict<K, V>* D) : D_(D), i_(0) {
  }
  void Next() {
    ++i_;
  }
  bool Done() {
    return i_ >= static_cast<int>(D_->items_.size());
  }
  K Key() {
    return D_->items_[i_].first;
  }
  V Value() {
    return D_->items_[i_].second;
  }

 private:
  Dict<K, V>* D_;
  int i_;
};

// Specialized functions
template <class V>
int find_by_key(std::vector<std::pair<Str*, V>>& items, Str* key) {
  for (int i = 0; i < items.size(); ++i) {
    if (str_equals(items[i].first, key)) {
      return i;
    }
  }
  return -1;
}

template <class V>
int find_by_key(std::vector<std::pair<int, V>>& items, int key) {
  for (int i = 0; i < items.size(); ++i) {
    if (items[i].first == key) {
      return i;
    }
  }
  return -1;
}

// Dict currently implemented by VECTOR OF PAIRS.  TODO: Use a real hash table,
// and measure performance.  The hash table has to beat this for small cases!
template <class K, class V>
class Dict {
 public:
  Dict() : items_() {
  }

  // d[key] in Python: raises KeyError if not found
  V index(K key) {
    int pos = find(key);
    if (pos == -1) {
      assert(0);
    } else {
      return items_[pos].second;
    }
  }

  // Get a key.
  // Returns nullptr if not found (Can't use this for non-pointer types?)
  V get(K key) {
    int pos = find(key);
    if (pos == -1) {
      return nullptr;
    } else {
      return items_[pos].second;
    }
  }

  // Get a key, but return a default if not found.
  // expr_parse.py uses this with OTHER_BALANCE
  V get(K key, V default_val) {
    int pos = find(key);
    if (pos == -1) {
      return default_val;
    } else {
      return items_[pos].second;
    }
  }

  // d->set(key, val) is like (*d)[key] = val;
  void set(K key, V val) {
    int pos = find(key);
    if (pos == -1) {
      items_.push_back(std::make_pair(key, val));
    } else {
      items_[pos].second = val;
    }
  }

  void remove(K key) {
    assert(0);
  }

  List<K>* keys() {
    assert(0);
  }

  // For AssocArray transformations
  List<V>* values() {
    assert(0);
  }

  void clear() {
    assert(0);
  }

  // std::unordered_map<K, V> m_;
  std::vector<std::pair<K, V>> items_;

 private:
  // returns the position in the array
  int find(K key) {
    return find_by_key(items_, key);
  }
};

template <class A, class B>
class Tuple2 {
 public:
  Tuple2(A a, B b) : a_(a), b_(b) {
  }
  A at0() {
    return a_;
  }
  B at1() {
    return b_;
  }

 private:
  A a_;
  B b_;
};

template <class A, class B, class C>
class Tuple3 {
 public:
  Tuple3(A a, B b, C c) : a_(a), b_(b), c_(c) {
  }
  A at0() {
    return a_;
  }
  B at1() {
    return b_;
  }
  C at2() {
    return c_;
  }

 private:
  A a_;
  B b_;
  C c_;
};

template <class A, class B, class C, class D>
class Tuple4 {
 public:
  Tuple4(A a, B b, C c, D d) : a_(a), b_(b), c_(c), d_(d) {
  }
  A at0() {
    return a_;
  }
  B at1() {
    return b_;
  }
  C at2() {
    return c_;
  }
  D at3() {
    return d_;
  }

 private:
  A a_;
  B b_;
  C c_;
  D d_;
};

// for posix::times()
template <class A, class B, class C, class D, class E>
class Tuple5 {
 public:
  Tuple5(A a, B b, C c, D d, E e) : a_(a), b_(b), c_(c), d_(d), e_(e) {
  }
  A at0() {
    return a_;
  }
  B at1() {
    return b_;
  }
  C at2() {
    return c_;
  }
  D at3() {
    return d_;
  }
  E at4() {
    return e_;
  }

 private:
  A a_;
  B b_;
  C c_;
  D d_;
  E e_;
};

//
// Overloaded free function len()
//

inline int len(const Str* s) {
  return s->len_;
}

template <typename T>
int len(const List<T>* L) {
  return L->v_.size();
}

template <typename K, typename V>
int len(const Dict<K, V>* d) {
  assert(0);
}

//
// Free functions
//

Str* str_concat(Str* a, Str* b);  // a + b when a and b are strings

Str* str_repeat(Str* s, int times);  // e.g. ' ' * 3

inline bool str_equals(Str* left, Str* right) {
  if (left->len_ == right->len_) {
    return memcmp(left->data_, right->data_, left->len_) == 0;
  } else {
    return false;
  }
}

inline bool str_equals0(const char* c_string, Str* s) {
  int n = strlen(c_string);
  if (s->len_ == n) {
    return memcmp(s->data_, c_string, n) == 0;
  } else {
    return false;
  }
}

inline bool maybe_str_equals(Str* left, Str* right) {
  if (left && right) {
    return str_equals(left, right);
  }

  if (!left && !right) {
    return true;  // None == None
  }

  return false;  // one is None and one is a Str*
}

inline Str* chr(int i) {
  char* buf = static_cast<char*>(malloc(2));
  buf[0] = i;
  buf[1] = '\0';
  return new Str(buf, 1);
}

inline int ord(Str* s) {
  assert(s->len_ == 1);
  // signed to unsigned conversion, so we don't get values like -127
  uint8_t c = static_cast<uint8_t>(s->data_[0]);
  return c;
}

// https://stackoverflow.com/questions/3919995/determining-sprintf-buffer-size-whats-the-standard/11092994#11092994
// Note: Python 2.7's intobject.c has an erroneous +6

// This is 13, but
// len('-2147483648') is 11, which means we only need 12?
const int kIntBufSize = CHAR_BIT * sizeof(int) / 3 + 3;

inline Str* str(int i) {
  char* buf = static_cast<char*>(malloc(kIntBufSize));
  int len = snprintf(buf, kIntBufSize, "%d", i);
  return new Str(buf, len);
}

inline Str* str(double f) {  // TODO: should be double
  assert(0);
}

// Display a quoted representation of a string.  word_.Pretty() uses it.
Str* repr(Str* s);

// TODO: There should be one str() and one repr() for every sum type, that
// dispatches on tag?  Or just repr()?

// Will need it for dict, but not tuple.
// inline int len(Dict* D) {
// }

bool _str_to_int(Str* s, int* result, int base);  // for testing only
int to_int(Str* s);
int to_int(Str* s, int base);

// int(a == b) used in arithmetic evaluator
inline int to_int(bool b) {
  return b;
}

inline bool to_bool(int i) {
  return i != 0;
}

inline bool to_bool(Str* s) {
  return s->len_ != 0;
}

inline double to_float(Str* s) {
  assert(0);
}

// e.g. ('a' in 'abc')
inline bool str_contains(Str* haystack, Str* needle) {
  // cstring-TODO: this not rely on NUL termination
  const char* p = strstr(haystack->data_, needle->data_);
  return p != nullptr;
}

// e.g. 'a' in ['a', 'b', 'c']
inline bool list_contains(List<Str*>* haystack, Str* needle) {
  int n = haystack->v_.size();
  for (int i = 0; i < n; ++i) {
    if (str_equals(haystack->index(i), needle)) {
      return true;
    }
  }
  return false;
}

// e.g. [None] * 3
template <typename T>
List<T>* list_repeat(T item, int times) {
  return new List<T>(item, times);
}

// list(L) copies the list
template <typename T>
List<T>* list(List<T>* other) {
  auto result = new List<T>();
  for (int i = 0; i < len(other); ++i) {
    result->set(i, other->index(i));
  }
  return result;
}

// ints, floats, enums like Kind
// e.g. 1 in [1, 2, 3]
template <typename T>
inline bool list_contains(List<T>* haystack, T needle) {
  int n = haystack->v_.size();
  for (int i = 0; i < n; ++i) {
    if (haystack->index(i) == needle) {
      return true;
    }
  }
  return false;
}

// STUB
template <typename K, typename V>
inline bool dict_contains(Dict<K, V>* haystack, K needle) {
  return find_by_key(haystack->items_, needle) != -1;
}

template <typename V>
List<Str*>* sorted(Dict<Str*, V>* d) {
  assert(0);
}

//
// Buf is StringIO
//

namespace mylib {  // MyPy artifact

// A class for interfacing Str* slices with C functions that expect a NUL
// terminated string.  It's meant to be used on the stack, like
//
// void f(Str* pat) {
//   Str0 c_pattern(pat);
//   int n = strlen(c_pattern.Get());
//
//   // copy of Str* is destroyed
// }
class Str0 {
 public:
  Str0(Str* s) : s_(s), nul_str_(nullptr) {
  }
  ~Str0() {
    if (nul_str_) {
      free(nul_str_);
    }
  }

  const char* Get() {  // caller should not modify this string!
    if (s_->IsNulTerminated()) {
      return s_->data_;
    } else {
      nul_str_ = static_cast<char*>(malloc(s_->len_ + 1));
      memcpy(nul_str_, s_->data_, s_->len_);
      nul_str_[s_->len_] = '\0';
      return nul_str_;
    }
  }

  Str* s_;
  char* nul_str_;
};

Tuple2<Str*, Str*> split_once(Str* s, Str* delim);

inline Str* NewStr(const char* s) {
  return new Str(s);
}

class LineReader {
 public:
  virtual Str* readline() = 0;
  virtual bool isatty() {
    return false;
  }
  virtual int fileno() {
    assert(0);  // shouldn't be called here
  }
};

class BufLineReader : public LineReader {
 public:
  explicit BufLineReader(Str* s) : s_(s), pos_(s->data_) {
  }
  virtual Str* readline();

 private:
  Str* s_;
  const char* pos_;

  DISALLOW_COPY_AND_ASSIGN(BufLineReader)
};

// Wrap a FILE*
class CFileLineReader : public LineReader {
 public:
  explicit CFileLineReader(FILE* f) : f_(f) {
  }
  virtual Str* readline();
  virtual int fileno() {
    return ::fileno(f_);
  }

 private:
  FILE* f_;

  DISALLOW_COPY_AND_ASSIGN(CFileLineReader)
};

extern LineReader* gStdin;

inline LineReader* Stdin() {
  if (gStdin == nullptr) {
    gStdin = new CFileLineReader(stdin);
  }
  return gStdin;
}

inline LineReader* open(Str* path) {
  Str0 path0(path);
  FILE* f = fopen(path0.Get(), "r");

  // TODO: Better error checking.  IOError?
  if (!f) {
    throw new AssertionError("file not found");
  }
  return new CFileLineReader(f);
}

class Writer {
 public:
  virtual void write(Str* s) = 0;
  virtual void flush() = 0;
  virtual bool isatty() = 0;
};

class BufWriter : public Writer {
 public:
  BufWriter() : data_(nullptr), len_(0) {
  }
  virtual void write(Str* s) override;
  virtual void flush() override {
  }
  virtual bool isatty() override {
    return false;
  }
  // For cStringIO API
  Str* getvalue() {
    if (data_) {
      Str* ret = new Str(data_, len_);
      reset();  // Invalidate this instance
      return ret;
    } else {
      // log('') translates to this
      // Strings are immutable so we can do this.
      return kEmptyString;
    }
  }

  // Methods to compile printf format strings to

  // To reuse the global gBuf instance
  // problem: '%r' % obj will recursively call asdl/format.py, which has its
  // own % operations
  void reset() {
    data_ = nullptr;  // make sure we get a new buffer next time
    len_ = 0;
  }

  // Note: we do NOT need to instantiate a Str() to append
  void write_const(const char* s, int len);

  // strategy: snprintf() based on sizeof(int)
  void format_d(int i);
  void format_s(Str* s);
  void format_r(Str* s);  // formats with quotes

  // looks at arbitrary type tags?  Is this possible
  // Passes "this" to functions generated by ASDL?
  void format_r(void* s);

 private:
  // Just like a string, except it's mutable
  char* data_;
  int len_;
};

// Wrap a FILE*
class CFileWriter : public Writer {
 public:
  explicit CFileWriter(FILE* f) : f_(f) {
  }
  virtual void write(Str* s) override;
  virtual void flush() override;
  virtual bool isatty() override;

 private:
  FILE* f_;

  DISALLOW_COPY_AND_ASSIGN(CFileWriter)
};

extern Writer* gStdout;

inline Writer* Stdout() {
  if (gStdout == nullptr) {
    gStdout = new CFileWriter(stdout);
  }
  return gStdout;
}

extern Writer* gStderr;

inline Writer* Stderr() {
  if (gStderr == nullptr) {
    gStderr = new CFileWriter(stderr);
  }
  return gStderr;
}

inline Str* hex_lower(int i) {
  assert(0);
}

inline Str* hex_upper(int i) {
  assert(0);
}

inline Str* octal(int i) {
  assert(0);
}

}  // namespace mylib

//
// Formatter for Python's %s
//

extern mylib::BufWriter gBuf;

// mycpp doesn't understand dynamic format strings yet
inline Str* dynamic_fmt_dummy() {
  return new Str("dynamic_fmt_dummy");
}

#endif  // MYLIB_H
