// mylib.h

#ifndef MYLIB_H
#define MYLIB_H

#include <assert.h>
#include <ctype.h>  // isalpha(), isdigit()
#include <stddef.h>  // size_t
#include <stdlib.h>  // malloc
#include <string.h>  // strlen
// https://stackoverflow.com/questions/3882346/forward-declare-file
#include <cstdio>  // FILE*
#include <vector>
#include <initializer_list>

class Str;
template <class T> class List;
template <class K, class V> class Dict;

// for hand-written code
void log(const char* fmt, ...);

// for generated code
void log(Str* fmt, ...);

void print(Str* s);

//
// TODO: Fill exceptions in
//

class IndexError {
};

class KeyError {
};

class EOFError {
};

class NotImplementedError {
};

class AssertionError {
};


//
// Data Types
//

class Str {
 public:
  Str(const char* data) : data_(data) {
    len_ = strlen(data);
  }

  Str(const char* data, int len) : data_(data), len_(len) {
  }

  // Get a string with one character
  Str* index(int i) {
    char* buf = static_cast<char*>(malloc(2));
    buf[0] = data_[i];
    buf[1] = '\0';
    return new Str(buf, 1);
  }

  // s[begin:]
  Str* slice(int begin) {
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

  // TODO: implement these.  With switch statement.
  Str* strip() {
    return nullptr;
  }
  Str* rstrip() {
    return nullptr;
  }

  bool startswith(Str* s) {
    assert(false);
    return true;
  }
  bool endswith(Str* s) {
    assert(false);
    return true;
  }
  bool isdigit() {
    if (len_ == 0) {
      return false;  // special case
    }
    for (int i = 0; i < len_; ++i) {
      if (! ::isdigit(data_[i])) {
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
      if (! ::isalpha(data_[i])) {
        return false;
      }
    }
    return true;
  }

  List<Str*>* splitlines(bool keep) {
    assert(keep == true);
    return nullptr;
  }

  Str* replace(Str* old, Str* new_str);
  Str* join(List<Str*>* items);

  bool contains(Str* needle);

  const char* data_;
  size_t len_;
};

// NOTE: This iterates over bytes.
class StrIter {
 public:
  StrIter(Str* s) : s_(s), i_(0) {
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
};

// TODO: Parameterize this by type.  I don't think we can use vector<>
// directly?  The method names are different.
template <class T>
class List {
 public:
  List() : v_() {
  };

  List(std::initializer_list<T> init) : v_() {
    for (T item : init) {
      v_.push_back(item);
    }
  }

  T index(int i) {
    if (i < 0) {
      int j = v_.size() + i;
      return v_.at(j);
    }
    return v_.at(i);  // checked version
  }

  // L[begin:]
  List* slice(int begin) {
    List* result = new List();
    for (int i = begin; i < v_.size(); i++) {
      result->v_.push_back(v_[i]);
    }
    return result;
  }

  void append(T item) {
    v_.push_back(item);
  }

  // Reconsider?
  // https://stackoverflow.com/questions/12600330/pop-back-return-value
  T pop() {
    assert(!v_.empty());
    T result = v_.back();
    v_.pop_back();
    return result;
  }

 //private:
  std::vector<T> v_;  // ''.join accesses this directly
};

template <class T>
class ListIter {
 public:
  ListIter(List<T>* L) : L_(L), i_(0) {
  };
  void Next() {
    i_++;
  }
  bool Done() {
    return i_ >= L_->v_.size();
  };
  T Value() {
    return L_->v_[i_];
  }

 private:
  List<T>* L_;
  int i_;
};

template <class K, class V>
class Dict {
 public:
  // TODO: Implement it!
  // Used unordered_map or what?
  V index(K key) {
    return values_[0];
  }

  V& operator[](K key) {
    return values_[0];
  }
 private:
  V values_[1];
};

template <class A, class B>
class Tuple2 {
 public:
  Tuple2(A a, B b) : a_(a), b_(b) {
  };
  A at0() { return a_; }
  B at1() { return b_; }

 private:
  A a_;
  B b_;
};

template <class A, class B, class C>
class Tuple3 {
 public:
  Tuple3(A a, B b, C c) : a_(a), b_(b), c_(c) {
  };
  A at0() { return a_; }
  B at1() { return b_; }
  C at2() { return c_; }

 private:
  A a_;
  B b_;
  C c_;
};

template <class A, class B, class C, class D>
class Tuple4 {
 public:
  Tuple4(A a, B b, C c, D d) : a_(a), b_(b), c_(c), d_(d) {
  };
  A at0() { return a_; }
  B at1() { return b_; }
  C at2() { return c_; }
  D at3() { return d_; }

 private:
  A a_;
  B b_;
  C c_;
  D d_;
};


//
// Overloaded free function len()
//

inline int len(Str* s) {
  return s->len_;
}

template <class T> int len(List<T>* L) {
  return L->v_.size();
}

//
// Free functions
//

Str* str_concat(Str* a, Str* b);  // a + b when a and b are strings

inline bool str_equals(Str* left, Str* right) {
  if (left->len_ == right->len_) {
    return memcmp(left->data_, right->data_, left->len_) == 0;
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

// TODO: Call itoa I guess.
inline Str* str(int i) {
  return new Str("");
}

// TODO: There should be one str() and one repr() for every sum type, that
// dispatches on tag?  Or just repr()?

// Will need it for dict, but not tuple.
//inline int len(Dict* D) {
//}

bool _str_to_int(Str* s, int* result);  // for testing only
int str_to_int(Str* s);

//
// Buf is StringIO
//

namespace mylib {  // MyPy artifact

class LineReader {
 public:
  virtual Str* readline() = 0;
};

class BufLineReader : public LineReader {
 public:
  BufLineReader(Str* s) : s_(s) {
  }
  virtual Str* readline();
 private:
  Str* s_;
};

// TODO: Rename Writer
class File {
 public:
  virtual void write(Str* s) = 0;
};

class Buf : public File {
 public:
  Buf() : data_(nullptr), len_(0) {
  };
  virtual void write(Str* s);
  Str* getvalue() { return new Str(data_, len_); }

 private:
  // Just like a string, except it's mutable
  char* data_;
  size_t len_;
};

// Wrap a FILE*
class CFile : public File {
 public:
  CFile(FILE* f) : f_(f) {
  };
  virtual void write(Str* s);

 private:
  FILE* f_;
};

extern File* gStdOut;

inline File* StdOut() {
  if (gStdOut == nullptr) {
    gStdOut = new CFile(stdout);
  }
  return gStdOut;
}

};

#endif  // MYLIB_H
