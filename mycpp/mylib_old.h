// mylib_old.h

#ifndef MYLIB_H
#define MYLIB_H

#include <assert.h>
#include <ctype.h>   // isalpha(), isdigit()
#include <stdlib.h>  // malloc
#include <string.h>  // strlen

#include <algorithm>  // sort() is templated
// https://stackoverflow.com/questions/3882346/forward-declare-file
#include <climits>  // CHAR_BIT
#include <cstdint>
#include <cstdio>  // FILE*
#include <initializer_list>
#include <vector>

#include "common.h"

// if this file is even included, we're using the old mylib
#define MYLIB_LEAKY 1
#include "mycpp/gc_types.h"  // for Obj

#ifdef DUMB_ALLOC
  #include "cpp/dumb_alloc.h"
  #define malloc dumb_malloc
  #define free dumb_free
#endif

class Str;

template <class T>
class List;

template <class K, class V>
class Dict;

template <class K, class V>
class DictIter;

bool are_equal(Str* left, Str* right);
bool str_equals(Str* left, Str* right);

namespace mylib {
template <typename V>
void dict_remove(Dict<Str*, V>* haystack, Str* needle);

template <typename V>
void dict_remove(Dict<int, V>* haystack, int needle);

};  // namespace mylib

extern Str* kEmptyString;

void print(Str* s);

// log() generates code that writes this
void println_stderr(Str* s);

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

#ifdef MYLIB_LEAKY
class Str : public gc_heap::Obj {
 public:
  Str(const char* data, int len)
      : gc_heap::Obj(Tag::FixedSize, gc_heap::kZeroMask, 0),
        len_(len),
        data_(data) {
  }

  explicit Str(const char* data) : Str(data, strlen(data)) {
  }

  // emulating gc_heap API
  void SetObjLenFromStrLen(int len) {
    len_ = len;
  }

  // Usage:
  // Str* s = OverAllocatedStr(10);
  // strcpy(s->data(), "foo");
  char* data() {
    return const_cast<char*>(data_);
  }

  // Important invariant: the buffer is of size len+1, so data[len] is OK to
  // access!  Not just data[len-1].  We use that to test if it's a C string.
  // note: "foo" and "foo\0" are both NUL-terminated.
  bool IsNulTerminated() {
    return data_[len_] == '\0';
  }

  // Get a string with one character
  Str* index_(int i) {
    if (i < 0) {
      i = len_ + i;
    }
    assert(i >= 0);
    assert(i < len_);  // had a problem here!

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
    begin = std::min(begin, len_);
    end = std::min(end, len_);

    assert(begin <= len_);
    assert(end <= len_);

    if (begin < 0) {
      begin = len_ + begin;
    }

    if (end < 0) {
      end = len_ + end;
    }

    begin = std::min(begin, len_);
    end = std::min(end, len_);

    begin = std::max(begin, 0);
    end = std::max(end, 0);

    assert(begin >= 0);
    assert(begin <= len_);

    assert(end >= 0);
    assert(end <= len_);

    int new_len = end - begin;

    // Tried to use std::clamp() here but we're not compiling against cxx-17
    new_len = std::max(new_len, 0);
    new_len = std::min(new_len, len_);

    /* printf("len(%d) [%d, %d] newlen(%d)\n",  len_, begin, end, new_len); */

    assert(new_len >= 0);
    assert(new_len <= len_);

    char* buf = static_cast<char*>(malloc(new_len + 1));
    memcpy(buf, data_ + begin, new_len);

    buf[new_len] = '\0';
    return new Str(buf, new_len);
  }

  Str* strip();
  Str* rstrip(Str* chars);
  Str* rstrip();

  #if 0
  Str* lstrip(Str* chars);
  Str* lstrip();
  #endif

  bool startswith(Str* s) {
    if (s->len_ > len_) {
      return false;
    }
    return memcmp(data_, s->data_, s->len_) == 0;
  }
  bool endswith(Str* s) {
    if (s->len_ > len_) {
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

  int find(Str* needle, int pos = 0) {
    assert(needle->len_ == 1);  // Oil's usage
    char c = needle->data_[0];
    for (int i = pos; i < len_; ++i) {
      if (data_[i] == c) {
        return i;
      }
    }
    return -1;
  }

  int rfind(Str* needle) {
    assert(needle->len_ == 1);  // Oil's usage
    char c = needle->data_[0];
    for (int i = len_ - 1; i >= 0; --i) {
      if (data_[i] == c) {
        return i;
      }
    }
    return -1;
  }

  Str* upper();
  Str* lower();
  Str* ljust(int width, Str* fillchar);
  Str* rjust(int width, Str* fillchar);

  int len_;  // reorder for alignment
  const char* data_;

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
//
// TODO(Jesse): I like the sound of getting rid of std:vector
//
template <class T>
class List : public gc_heap::Obj {
 public:
  // Note: constexpr doesn't work because the std::vector destructor is
  // nontrivial
  List() : gc_heap::Obj(Tag::FixedSize, gc_heap::kZeroMask, 0), v_() {
    // Note: this seems to INCREASE the number of 'new' calls.  I guess because
    // many 'spids' lists aren't used?
    // v_.reserve(64);
  }

  // Used by list_repeat
  List(T item, int n)
      : gc_heap::Obj(Tag::FixedSize, gc_heap::kZeroMask, 0), v_(n, item) {
  }

  List(std::initializer_list<T> init)
      : gc_heap::Obj(Tag::FixedSize, gc_heap::kZeroMask, 0), v_() {
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

  // L[i]
  T index_(int i) const {
    if (i < 0) {
      // User code doesn't result in mylist[-1], but Oil's own code does
      int j = v_.size() + i;
      return v_.at(j);
    }
    return v_.at(i);  // checked version
  }

  // L.index(i) -- Python method
  int index(T value) const {
    int len = v_.size();
    for (int i = 0; i < len; i++) {
      // TODO: this doesn't work for strings!
      if (v_[i] == value) {
        return i;
      }
    }
    throw new ValueError();
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
  #ifdef ALLOC_LOG
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
      // TODO(Jesse): Probably shouldn't crash if we try to pop a List with
      // nothing on it
      InvalidCodePath();
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
    mysort(&v_);
  }

  // in osh/string_ops.py
  void reverse() {
    int n = v_.size();
    for (int i = 0; i < n / 2; ++i) {
      // log("swapping %d and %d", i, n-i);
      T tmp = v_[i];
      int j = n - 1 - i;
      v_[i] = v_[j];
      v_[j] = tmp;
    }
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

// TODO: A proper dict index should get rid of this unusual sentinel scheme.
// The index can be -1 on deletion, regardless of the type of the key.

template <class K, class V>
void dict_next(DictIter<K, V>* it, const std::vector<std::pair<K, V>>& items) {
  ++it->i_;
}

template <class V>
void dict_next(DictIter<Str*, V>* it,
               const std::vector<std::pair<Str*, V>>& items) {
  while (true) {
    ++it->i_;
    if (it->Done()) {
      break;
    }
    if (items[it->i_].first) {  // not nullptr
      break;
    }
  }
}

template <class K, class V>
bool dict_done(DictIter<K, V>* it, const std::vector<std::pair<K, V>>& items) {
  int n = items.size();
  return it->i_ >= n;
}

template <class V>
bool dict_done(DictIter<Str*, V>* it,
               const std::vector<std::pair<Str*, V>>& items) {
  int n = items.size();
  if (it->i_ >= n) {
    return true;
  }
  for (int j = it->i_; j < n; ++j) {
    if (items[j].first) {  // there's still something left
      return false;
    }
  }
  return true;
}

template <class K, class V>
class DictIter {
 public:
  explicit DictIter(Dict<K, V>* D) : D_(D), i_(0) {
  }
  void Next() {
    dict_next(this, D_->items_);
  }
  bool Done() {
    return dict_done(this, D_->items_);
  }
  K Key() {
    return D_->items_[i_].first;
  }
  V Value() {
    return D_->items_[i_].second;
  }

  Dict<K, V>* D_;
  int i_;
};

// Specialized functions
template <class V>
int find_by_key(const std::vector<std::pair<Str*, V>>& items, Str* key) {
  int n = items.size();
  for (int i = 0; i < n; ++i) {
    Str* s = items[i].first;  // nullptr for deleted entries
    if (s && str_equals(s, key)) {
      return i;
    }
  }
  return -1;
}

template <class V>
int find_by_key(const std::vector<std::pair<int, V>>& items, int key) {
  int n = items.size();
  for (int i = 0; i < n; ++i) {
    if (items[i].first == key) {
      return i;
    }
  }
  return -1;
}

template <class V>
List<Str*>* dict_keys(const std::vector<std::pair<Str*, V>>& items) {
  auto result = new List<Str*>();
  int n = items.size();
  for (int i = 0; i < n; ++i) {
    Str* s = items[i].first;  // nullptr for deleted entries
    if (s) {
      result->append(s);
    }
  }
  return result;
}

template <class V>
List<V>* dict_values(const std::vector<std::pair<Str*, V>>& items) {
  auto result = new List<V>();
  int n = items.size();
  for (int i = 0; i < n; ++i) {
    auto& pair = items[i];
    if (pair.first) {
      result->append(pair.second);
    }
  }
  return result;
}

// Dict currently implemented by VECTOR OF PAIRS.  TODO: Use a real hash table,
// and measure performance.  The hash table has to beat this for small cases!
template <class K, class V>
class Dict : public gc_heap::Obj {
 public:
  Dict() : gc_heap::Obj(Tag::FixedSize, gc_heap::kZeroMask, 0), items_() {
  }

  // Dummy
  Dict(std::initializer_list<K> keys, std::initializer_list<V> values)
      : gc_heap::Obj(Tag::FixedSize, gc_heap::kZeroMask, 0), items_() {
  }

  // d[key] in Python: raises KeyError if not found
  V index_(K key) {
    int pos = find(key);
    if (pos == -1) {
      throw new KeyError();
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
    mylib::dict_remove(this, key);
  }

  List<K>* keys() {
    return dict_keys(items_);
  }

  // For AssocArray transformations
  List<V>* values() {
    return dict_values(items_);
  }

  void clear() {
    items_.clear();
  }

  // std::unordered_map<K, V> m_;
  std::vector<std::pair<K, V>> items_;

 private:
  // returns the position in the array
  int find(K key) {
    return find_by_key(items_, key);
  }
};

template <typename K, typename V>
Dict<K, V>* NewDict() {
  auto self = gc_heap::Alloc<Dict<K, V>>();
  return self;
}

template <typename K, typename V>
Dict<K, V>* NewDict(std::initializer_list<K> keys,
                    std::initializer_list<V> values) {
  // TODO(Jesse): Is this NotImplemented() or InvalidCodePath() ?
  assert(0);  // Uncalled
}

#endif  // MYLIB_LEAKY

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

//
// Overloaded free function len()
//

#ifdef MYLIB_LEAKY
inline int len(const Str* s) {
  return s->len_;
}

template <typename T>
inline int len(const List<T>* L) {
  // inline int len(List<T>* L) {
  return L->v_.size();
}

template <typename K, typename V>
inline int len(const Dict<K, V>* d) {
  assert(0);
}

template <typename V>
inline int len(const Dict<Str*, V>* d) {
  int len = 0;
  int n = d->items_.size();
  for (int i = 0; i < n; ++i) {
    Str* s = d->items_[i].first;  // nullptr for deleted entries
    if (s) {
      len++;
    }
  }
  return len;
}
#endif

//
// Free functions
//

Str* str_concat(Str* a, Str* b);           // a + b when a and b are strings
Str* str_concat3(Str* a, Str* b, Str* c);  // for os_path::join()

Str* str_repeat(Str* s, int times);  // e.g. ' ' * 3

#if MYLIB_LEAKY
inline bool str_equals(Str* left, Str* right) {
  if (left->len_ == right->len_) {
    return memcmp(left->data_, right->data_, left->len_) == 0;
  } else {
    return false;
  }
}

namespace id_kind_asdl {
enum class Kind;
};

inline bool are_equal(id_kind_asdl::Kind left, id_kind_asdl::Kind right);

inline bool are_equal(int left, int right) {
  return left == right;
  ;
}

inline bool are_equal(Str* left, Str* right) {
  return str_equals(left, right);
}

inline bool are_equal(Tuple2<Str*, int>* t1, Tuple2<Str*, int>* t2) {
  bool result = are_equal(t1->at0(), t2->at0());
  result = result && (t1->at1() == t2->at1());
  return result;
}
#endif

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
// Notes:
// - Python 2.7's intobject.c has an erroneous +6
// - This is 13, but len('-2147483648') is 11, which means we only need 12?
// - This formula is valid for octal(), because 2^(3 bits) = 8
const int kIntBufSize = CHAR_BIT * sizeof(int) / 3 + 3;

inline Str* str(int i) {
  char* buf = static_cast<char*>(malloc(kIntBufSize));
  int len = snprintf(buf, kIntBufSize, "%d", i);
  return new Str(buf, len);
}

inline Str* str(double f) {  // TODO: should be double
  NotImplemented();          // Uncalled
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
  assert(s->IsNulTerminated());
  double result = atof(s->data_);
  return result;
}

// e.g. ('a' in 'abc')
inline bool str_contains(Str* haystack, Str* needle) {
  // Common case
  if (needle->len_ == 1) {
    return memchr(haystack->data_, needle->data_[0], haystack->len_);
  }

  // General case. TODO: We could use a smarter substring algorithm.
  if (needle->len_ > haystack->len_) {
    return false;
  }

  const char* end = haystack->data_ + haystack->len_;
  const char* last_possible = end - needle->len_;
  const char* p = haystack->data_;

  while (p <= last_possible) {
    if (memcmp(p, needle->data_, needle->len_) == 0) {
      return true;
    }
    p++;
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
    result->set(i, other->index_(i));
  }
  return result;
}

template <typename T>
bool list_contains(List<T>* haystack, T needle) {
  int n = haystack->v_.size();
  for (int i = 0; i < n; ++i) {
    if (are_equal(haystack->index_(i), needle)) {
      return true;
    }
  }
  return false;
}

template <typename T>
bool list_contains(List<T>* haystack, T* needle) {
  bool result = false;

  if (needle) {
    result = list_contains(haystack, *needle);
  }

  return result;
}

template <typename K, typename V>
inline bool dict_contains(Dict<K, V>* haystack, K needle) {
  return find_by_key(haystack->items_, needle) != -1;
}

template <typename V>
List<Str*>* sorted(Dict<Str*, V>* d) {
  auto keys = d->keys();
  keys->sort();
  return keys;
}

inline int int_cmp(int a, int b) {
  if (a == b) {
    return 0;
  }
  return a < b ? -1 : 1;
}

// Used by [[ a > b ]] and so forth
inline int str_cmp(Str* a, Str* b) {
  int min = std::min(a->len_, b->len_);
  if (min == 0) {
    return int_cmp(a->len_, b->len_);
  }
  int comp = memcmp(a->data_, b->data_, min);
  if (comp == 0) {
    return int_cmp(a->len_, b->len_);  // tiebreaker
  }
  return comp;
}

// Hm std::sort() just needs true/false, not 0, 1, 1.
inline bool _cmp(Str* a, Str* b) {
  return str_cmp(a, b) < 0;
}

// specialization for Str only
inline void mysort(std::vector<Str*>* v) {
  std::sort(v->begin(), v->end(), _cmp);
}

//
// Buf is StringIO
//

namespace mylib {  // MyPy artifact

template <typename V>
inline void dict_remove(Dict<Str*, V>* haystack, Str* needle) {
  int pos = find_by_key(haystack->items_, needle);
  if (pos == -1) {
    return;
  }
  haystack->items_[pos].first = nullptr;
}

// TODO: how to do the int version of this?  Do you need an extra bit?
template <typename V>
inline void dict_remove(Dict<int, V>* haystack, int needle) {
  NotImplemented();
}

Tuple2<Str*, Str*> split_once(Str* s, Str* delim);

// Emulate GC API so we can reuse bindings

inline Str* AllocStr(int len) {
  char* buf = static_cast<char*>(malloc(len + 1));
  memset(buf, 0, len + 1);
  return new Str(buf, len);
}

inline Str* OverAllocatedStr(int len) {
  // Here they are identical, but in gc_heap.cc they're different
  return AllocStr(len);
}

inline Str* StrFromC(const char* s, int len) {
  // take ownership (but still leaks)
  char* buf = static_cast<char*>(malloc(len + 1));
  memcpy(buf, s, len);
  buf[len] = '\0';
  return new Str(buf, len);
}

inline Str* StrFromC(const char* s) {
  return StrFromC(s, strlen(s));
}

// emulate gc_heap API for ASDL

template <typename T>
List<T>* NewList() {
  return new List<T>();
}

template <typename T>
List<T>* NewList(std::initializer_list<T> init) {
  return new List<T>(init);
}

class LineReader {
 public:
  virtual Str* readline() = 0;
  virtual bool isatty() {
    return false;
  }

  virtual int fileno() {
    NotImplemented();
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
  FILE* f = fopen(path->data_, "r");

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
  void format_o(int i);
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
  char* buf = static_cast<char*>(malloc(kIntBufSize));
  int len = snprintf(buf, kIntBufSize, "%x", i);
  return new Str(buf, len);
}

inline Str* hex_upper(int i) {
  char* buf = static_cast<char*>(malloc(kIntBufSize));
  int len = snprintf(buf, kIntBufSize, "%X", i);
  return new Str(buf, len);
}

inline Str* octal(int i) {
  char* buf = static_cast<char*>(malloc(kIntBufSize));
  int len = snprintf(buf, kIntBufSize, "%o", i);
  return new Str(buf, len);
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
