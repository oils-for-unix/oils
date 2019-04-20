// Target Language Constructs
//
// We're generating a subset of C++.
//
// - Done:
//   - initializer lists
//   - exceptions
//   - default arguments
//   - namespaces
//
// - advanced:
//   - What do Python closures get translated to?  Oil uses them in a few
//     places, e.g. for the readline callbacks.
//   - C++ 20 coroutines (but we're almost certainly not using this)

#include <stdarg.h>  // va_list, etc.
#include <stdio.h>  // vprintf

#include <initializer_list>
#include <vector>

#include <stdexcept>

void log(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  vprintf(fmt, args);
  va_end(args);
  printf("\n");
}

class List {
 public:
  List(std::initializer_list<int> init)
      : v_() {

    for (int i : init) {
      v_.push_back(i);
    }
  }
  std::vector<int> v_;
};

template <class T>
class Array {
 public:
  Array() : v_() {
  }

  Array(std::initializer_list<T> init)
      : v_() {

    for (T i : init) {
      v_.push_back(i);
    }
  }

  void append(T item) {
    v_.push_back(item);
  }

  int size() {
    return v_.size();
  }

  std::vector<T> v_;
};

class ParseError {
 public:
  ParseError(const char* reason) : reason_(reason) {
  }
  const char* reason() const { return reason_; }

 private:
  const char* reason_;
};

// https://stackoverflow.com/questions/8480640/how-to-throw-a-c-exception
int compare(int a, int b) {
  if ( a < 0 || b < 0 ) {
    throw std::invalid_argument("received negative value");
  }
  return a < b;
}

int parse(const char* text) {
  if (text[0] == 'f') {
    throw ParseError("started with f");
  }
  return 0;
}

void except_demo() {
  log("compare(3, 1): %d", compare(1, 3));
  log("compare(5, 4): %d", compare(5, 4));

  try {
    log("compare(-1, 3): %d", compare(-1, 3));
  }
  catch (const std::invalid_argument& e) {
    log("Got exception: %s", e.what());
  }

  log("");

  try {
    log("parse('foo'): %d", parse("foo"));
  }
  catch (const ParseError& e) {
    log("Got exception: %s", e.reason());
  }

  try {
    log("parse('bar'): %d", parse("bar"));
  }
  catch (const ParseError& e) {
    log("Got exception: %s", e.reason());
  }
}

void template_demo() {
  Array<int> a;
  a.append(1);
  a.append(2);
  a.append(3);
  log("a.size() = %d", a.size());

  Array<List*> a2;
  a2.append(new List {1, 2, 3});
  a2.append(new List {4, 5, 6});
  log("a2.size() = %d", a2.size());
}

void f(int a, int b = -1, const char* s = nullptr) {
  log("");
  log("a = %d", a);
  log("b = %d", b);
  log("s = %p", s);
}

void default_args_demo() {
  f(42, 43, "foo");
  f(42, 43);
  f(42);
}

namespace core {
  namespace util {
    void p_die(const char* s) {
      log("p_die %s", s);
    }
  }
}

namespace tdop {
  using core::util::p_die;

  class Parser {
   public:
    Parser(int token) : token_(token) {
      log("Parser %d", token);
      p_die("Parser");
    }
    int token_;
  };
}

namespace typed_arith_parse {
  //using namespace core;  This makes EVERYTHING available.

  namespace util = core::util;

  // This lets us use "Parser""
  using tdop::Parser;

  void namespace_demo() {
    log("");
    log("namespace_demo()");
    f(42);
    auto p = new tdop::Parser(42);
    auto p2 = new Parser(43);

    util::p_die("ns");
  }
}

// Conclusion: every Python module should have is own namespace
//
// from core.util import log => using core::util::log
// from core import util => namespace util = core::util;


int main(int argc, char **argv) {
  log("sizeof(int): %d", sizeof(int));
  log("sizeof(int*): %d", sizeof(int*));
  log("");

  List l {1, 2, 3};

  // TODO: How to do this?

  // Dict d {{"key", 1}, {"val", 2}};

  log("size: %d", l.v_.size());
  log("");

  except_demo();

  log("");
  template_demo();

  log("");
  default_args_demo();
  typed_arith_parse::namespace_demo();
}
