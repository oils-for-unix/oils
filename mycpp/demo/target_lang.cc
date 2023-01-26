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

#include <sys/mman.h>  // mmap()

#include <initializer_list>
#include <memory>  // shared_ptr
#include <stdexcept>
#include <unordered_map>
#include <vector>

//#include "cpp/dumb_alloc.h"
#include "mycpp/runtime.h"
#include "mycpp/smartptr.h"
#include "vendor/greatest.h"

using std::unordered_map;

class RootingScope2 {
 public:
  RootingScope2() {
  }
  RootingScope2(const char* func_name) {
    log(">>> %s", func_name);
  }
  ~RootingScope2() {
  }
};

#define ROOTING_REPORT 1

#if ROOTING_REPORT
  #define FUNC_NAME_2() __PRETTY_FUNCTION__
#else
  #define FUNC_NAME_2()
#endif

class MyList {
 public:
  MyList(std::initializer_list<int> init) : v_() {
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

  Array(std::initializer_list<T> init) : v_() {
    for (T i : init) {
      v_.push_back(i);
    }
  }

  void append(T item) {
    RootingScope2 _r(FUNC_NAME_2());

    v_.push_back(item);
  }

  int size() {
    return v_.size();
  }

  std::vector<T> v_;
};

class FatalError {};

class ParseError : public FatalError {
 public:
  ParseError(const char* reason) : reason_(reason) {
  }
  const char* reason() const {
    RootingScope2 _r(FUNC_NAME_2());

    return reason_;
  }

 private:
  const char* reason_;
};

// https://stackoverflow.com/questions/8480640/how-to-throw-a-c-exception
int compare(int a, int b) {
  if (a < 0 || b < 0) {
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

void throw_fatal() {
  throw FatalError();
}

void except_subclass_demo() {
  try {
    throw_fatal();
    // parse("f");
  } catch (ParseError& e) {
    // Doesn't get caught.  Does this rely on RTTI, or is it static?
    // I think it's static but increases the size of the exception table.
    log("Got ParseError: %s", e.reason());
  }
}

TEST except_demo() {
  int num_caught = 0;

  log("compare(3, 1): %d", compare(1, 3));
  log("compare(5, 4): %d", compare(5, 4));

  try {
    log("compare(-1, 3): %d", compare(-1, 3));
  } catch (const std::invalid_argument& e) {
    log("Got exception: %s", e.what());
    num_caught++;
  }

  log("");

  try {
    log("parse('foo'): %d", parse("foo"));
  } catch (const ParseError& e) {
    log("Got exception: %s", e.reason());
    num_caught++;
  }

  try {
    log("parse('bar'): %d", parse("bar"));
  } catch (const ParseError& e) {
    log("Got exception: %s", e.reason());
    num_caught++;  // we don't get here
  }

  try {
    except_subclass_demo();
  } catch (const FatalError& e) {
    log("Got FatalError");
    num_caught++;
  }

  ASSERT_EQ_FMT(3, num_caught, "%d");

  PASS();
}

TEST template_demo() {
  Array<int> a;
  a.append(1);
  a.append(2);
  a.append(3);
  log("a.size() = %d", a.size());

  Array<MyList*> a2;
  a2.append(new MyList{1, 2, 3});
  a2.append(new MyList{4, 5, 6});
  log("a2.size() = %d", a2.size());

  PASS();
}

// prototype
void f(int a, int b = -1, const char* s = nullptr);

void f(int a, int b, const char* s) {
  log("");
  log("a = %d", a);
  log("b = %d", b);
  log("s = %p", s);
}

class Foo {
 public:
  // Is there any downside to these default args?
  // Only for virtual functions.  Note that they are re-evaluated at each call
  // site, which is fine.
  //
  // https://google.github.io/styleguide/cppguide.html#Default_Arguments
  Foo(int i, bool always_strict = false);

  void Print() {
    log("i = %d", i);
    log("always_strict = %d", always_strict);
  }

  int i;
  bool always_strict;
};

Foo::Foo(int i, bool always_strict) : i(i), always_strict(always_strict) {
}

TEST default_args_demo() {
  f(42, 43, "foo");
  f(42, 43);
  f(42);

  Foo a(98);
  a.Print();
  Foo b(99, true);
  b.Print();

  PASS();
}

namespace core {
namespace util {
void p_die(const char* s) {
  log("p_die %s", s);
}
}  // namespace util
}  // namespace core

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
}  // namespace tdop

namespace typed_arith_parse {
// using namespace core;  This makes EVERYTHING available.

namespace util = core::util;

// This lets us use "Parser""
using tdop::Parser;

TEST namespace_demo() {
  log("");
  log("namespace_demo()");
  f(42);
  auto unused1 = new tdop::Parser(42);
  auto unused2 = new Parser(43);
  (void)unused1;
  (void)unused2;

  util::p_die("ns");

  PASS();
}
}  // namespace typed_arith_parse

// Conclusion: every Python module should have is own namespace
//
// from core.util import log => using core::util::log
// from core import util => namespace util = core::util;

// test out the size of 5 uint16_t.  OK it's actually padded, which is nice!
// Because there is no big element.
struct Extent {
  uint16_t s_line_id;
  uint16_t s_col;
  uint16_t e_line_id;
  uint16_t e_col;
  uint16_t src_id;
};

class expr__Const {
 public:
  expr__Const(int i) : i_(i) {
  }
  int i_;
};

namespace expr {
typedef expr__Const Const;
}

using std::make_shared;
using std::shared_ptr;

shared_ptr<expr__Const> f(shared_ptr<expr__Const> arg) {
  log("arg.use_count() = %d", arg.use_count());
  return shared_ptr<expr__Const>(new expr__Const(arg->i_ + 10));
}

TEST shared_ptr_demo() {
  std::shared_ptr<expr__Const> e = make_shared<expr__Const>(5);
  log("e->i_ = %d", e->i_);
  log("e.use_count() = %d", e.use_count());

  // 16, not 24?
  // These are contiguous.
  log("sizeof(e) = %zu", sizeof(e));
  log("");

  std::shared_ptr<expr__Const> e2(new expr__Const(7));
  log("e2->i_ = %d", e2->i_);
  log("e2.use_count() = %d", e2.use_count());
  log("sizeof(e2) = %zu", sizeof(e2));
  log("");

  std::shared_ptr<expr__Const> e3 = f(e2);

  log("e3->i_ = %d", e3->i_);
  log("e3.use_count() = %d", e3.use_count());
  log("sizeof(e3) = %zu", sizeof(e3));
  log("");

  PASS();
}

TEST map_demo() {
  unordered_map<int, int> m;
  log("m.size = %d", m.size());

  // Hm integers have a hash function
  m[3] = 4;
  m[5] = 9;
  log("m.size = %d", m.size());

  // Hm you always get the pairs
  // Should this be const auto& or something?
  for (auto item : m) {
    log("iterating %d %d", item.first, item.second);
  }

  log("---");

  unordered_map<Extent*, int> m2;
  log("m2.size = %d", m2.size());

  // hm do I want this operator overloading?
  m2[nullptr] = 42;
  log("m2.size = %d", m2.size());

  log("retrieved = %d", m2[nullptr]);

  PASS();
}

TEST sizeof_demo() {
  log("sizeof(int): %d", sizeof(int));
  log("sizeof(int*): %d", sizeof(int*));
  log("sizeof(Extent): %d", sizeof(Extent));
  log("");

  // Good, this is 50.
  Extent ext_array[5];
  log("sizeof(ext_array): %d", sizeof(ext_array));

  PASS();
}

TEST test_misc() {
  MyList l{1, 2, 3};
  log("size: %d", l.v_.size());
  log("");

  // Dict literal syntax?
  // Dict d {{"key", 1}, {"val", 2}};

  log("");
  expr::Const c(42);
  log("expr::Const = %d", c.i_);

  // dumb_alloc::Summarize();

  PASS();
}

struct Point {
  int x;
  int y;
};

// structs don't have any constructors, so don't need any constexpr stuff
constexpr Point p = {3, 4};

// members must be public to allow initializer list
class PointC {
 public:
  // constructor is allowed
  // needs to be constexpr
  constexpr PointC(int x, int y) : x_(x), y_(y) {
  }
  // this is allowed too
  int get_x() {
    return x_;
  }
  // this is allowed too
  virtual int mag() const {
    return x_ * x_ + y_ * y_;
  }

  int x_;
  int y_;
};

constexpr PointC pc = {5, 6};

class SubPointC : public PointC {
 public:
  constexpr SubPointC(int x, int y) : PointC(x, y) {
  }
  virtual int mag() const {
    return 0;
  }
};

constexpr SubPointC sub = {7, 8};

class Compound {
 public:
  PointC c1;
  PointC c2;
};

// This works, but what about pointers?
constexpr Compound c = {{0, 1}, {8, 9}};

TEST static_literals() {
  ASSERT_EQ(3, p.x);
  ASSERT_EQ(4, p.y);

  ASSERT_EQ(5, pc.x_);
  ASSERT_EQ(6, pc.y_);

  // I'm surprised virtual functions are allowed!  We're compiling with
  // -std=c++11.
  // But this is just curiosity.  We don't need this in ASDL.
  ASSERT_EQ_FMT(61, pc.mag(), "%d");

  ASSERT_EQ_FMT(0, sub.mag(), "%d");

  ASSERT_EQ(0, c.c1.x_);
  ASSERT_EQ(1, c.c1.y_);
  ASSERT_EQ(8, c.c2.x_);
  ASSERT_EQ(9, c.c2.y_);

  PASS();
}

enum class Color_e { red, blue };

TEST enum_demo() {
  Color_e c1 = Color_e::red;
  Color_e c2 = Color_e::blue;
  int array[2] = {3, 4};

  // You can cast these strong enums to an integer.  We don't do that in the
  // MyPy source, but maybe we could?  It's kind of a pain though.

  log("c1 %d", static_cast<int>(c1));
  log("c2 %d", static_cast<int>(c2));

  log("array[c1] %d", array[static_cast<int>(c1)]);

  PASS();
}

class Node {
 public:
  int i;
  int j;
  Node* left;
  int k;
  // padding here on 64-bit, but not 32-bit
  Node* right;
};

#if 0
constexpr uint16_t Node_mask() {
  uint16_t mask = 0;

  constexpr int stride = sizeof(void*);

  constexpr int o1 = offsetof(Node, left);
  static_assert(o1 % stride == 0, "oops");

  constexpr int o2 = offsetof(Node, right);
  static_assert(o2 % stride == 0, "oops");

  constexpr int b1 = o1 / stride;
  constexpr int b2 = o2 / stride;

  mask |= 1 << b1;
  mask |= 1 << b2;

  return mask;
}

#else

// C++ 11 version has to be a single expression!

constexpr uint16_t Node_mask() {
  return (1 << (offsetof(Node, left) / sizeof(void*)) |
          1 << (offsetof(Node, right) / sizeof(void*)));
}

#endif

void print_bin(int n) {
  for (int i = 15; i >= 0; --i) {
    if (n & (1 << i))
      putchar('1');
    else
      putchar('0');
  }
  putchar('\n');
}

TEST field_mask_demo() {
  int c1 = offsetof(Node, left);
  int c2 = offsetof(Node, right);
  log("c1 = %d, c2 = %d, sizeof(void*) = %d", c1, c2, sizeof(void*));

  log("Node_mask");
  print_bin(Node_mask());

  PASS();
}

class Base {
 public:
  Base(int i) : GC_CLASS_FIXED(header_, kZeroMask, kNoObjLen), i(i) {
  }
  GC_OBJ(header_);
  int i;
  Node* left;
  Node* right;
};

class Derived : public Base {
 public:
  Derived(int i, int j) : Base(i), j(j) {
    // annoying: should be in initializer list
    FIELD_MASK(header_) |= 0x5;
  }
  int j;
  Node* three;
};

// Demonstrate problem with Local<T>
#if 0
TEST smartptr_inheritance_demo() {
  Local<Base> b = Alloc<Base>(2);
  Local<Derived> d = Alloc<Derived>(4, 5);

  ASSERT_EQ_FMT(2, b->i, "%d");

  ASSERT_EQ_FMT(4, d->i, "%d");
  ASSERT_EQ_FMT(5, d->j, "%d");

  ASSERT_EQ_FMT(0x9, b->field_mask_, "%d");
  ASSERT_EQ_FMT(0x5, d->field_mask_, "%d");

  PASS();
}
#endif

char* realloc(char* buf, size_t num_bytes) {
  void* result = mmap(nullptr, num_bytes, PROT_READ | PROT_WRITE,
                      MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  memcpy(result, buf, num_bytes);

  // Now make it unreadable
  int m = mprotect(buf, num_bytes, PROT_NONE);
  log("mprotect = %d", m);

  return static_cast<char*>(result);
}

TEST mmap_demo() {
  size_t num_bytes = 1;

  void* tmp = mmap(nullptr, num_bytes, PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  char* space = static_cast<char*>(tmp);

  *space = 42;

  log("space %p", space);

  log("value = %d", *space);

  space = realloc(space, num_bytes);
  log("value = %d", *space);

  // Can't use this anymore
  char* bad = static_cast<char*>(tmp);
  (void)bad;

  PASS();
}

TEST comma_demo() {
  auto i = 3;
  auto k = (i++, 5);
  log("k = %d", k);

  auto n = new Node();
  log("n = %p, n->i = %d, n->j = %d", n, n->i, n->j);

  // Hacky workaround ... actually this sorta works.  Gah.
  Node* tmp;
  auto n2 = (tmp = new Node(), tmp->i = 42, tmp);
  log("n2 = %p, n2->i = %d, n2->j = %d", n2, n2->i, n2->j);

  PASS();
}

// Trick here to print types at compile time
//
// https://stackoverflow.com/questions/60203857/print-a-types-name-at-compile-time-without-aborting-compilation

template <typename T>
[[gnu::warning("your type here")]] bool print_type() {
  return true;
}

TEST signed_unsigned_demo() {
  char c = '\xff';
  log("c = %d", c);
  log("c = %u", c);
  log("c > 127 = %d", c > 127);             // FALSE because it's char
  log("'\\xff' > 127 = %d", '\xff' > 127);  // also FALSE

#if 0
  bool b1 = print_type<decltype(c)>();

  // The type of literal '\xff' is 'char'
  bool b2 = print_type<decltype('\xff')>();

  log("b1 = %d", b1);
  log("b2 = %d", b2);
#endif

  PASS();
}

class Object {
 public:
  uint32_t header;
};

class Writer : public Object {
 public:
  // This vtable causes the quirk!
#if 1
  virtual int f() {
    return 42;
  }
#endif
};

void RootGlobalVar(Object* root) {
  // Super weird behavior!!!  The param root is 8 bytes ahead of the argument
  // gStdout!
  log("root = %p", root);
}

Writer* gStdout = nullptr;

Writer* Stdout() {
  if (gStdout == nullptr) {
    gStdout = new Writer();
    log("gStdout = %p", gStdout);

    log("no cast");
    RootGlobalVar(gStdout);
    log("");

    log("reinterpret_cast");
    RootGlobalVar(reinterpret_cast<Object*>(gStdout));
    log("");

    log("static_cast");
    RootGlobalVar(static_cast<Object*>(gStdout));
    log("");
  }
  return gStdout;
}

TEST param_passing_demo() {
  Writer* writer = Stdout();
  log("writer %p", writer);
  log("");

  // Same behavior: surprising!
  Object* obj = writer;
  log("obj %p", obj);
  log("");

  PASS();
}

#define ENUM(name, schema)

#define SUM(name, ...)

#define VARIANT(...)

#define USE(path)

#define SUM_NS(name)

#define PROD(name) struct name

#define SCHEMA(name)

TEST tea_macros_demo() {
  // The preprocessor does NOT expand this.  Instead we have a separate parser
  // that does it.  Hm not bad.
  //
  // Problem: the processor has to expand imports.

  USE("frontend/syntax.asdl");

  // Without commas

  ENUM(
      suffix_op,

      Nullary % Token |
          Unary {
            Token word;
            Word arg_word
          }

  );

  // More natural comma syntax.  Although less consistent with C++.
  // TODO: See what clang-format does on these.
  // Oh it treats:
  // - % and | as binary operators
  // - ; breaks a line but comma doesn't , which I might not want
  //
  // OK () and , looks better, but no line breaking.  Maybe there is a
  // clang-format option.
  //
  // Enabled WhitespaceSensitiveMacros for now.

  SUM(suffix_op,
      Nullary #Token,
      Unary(Token word, Word arg_word),
      Static(Token tok, Str arg)
  );

  SUM(suffix_op,

      Nullary #Token;
      Unary {
        Token word;
        Word arg_word;
      }
      Static {
        Token tok;
        Str arg;
      }
  );

  // The C++ compiler parses and validates these
  // Problem: recursive types and so forth.  We would need forward declarations
  // and all that?
  // It's also a bit more verbose.
  // How to do the % reference?  typedef?

  PROD(Token) {
    int id;
    Str val;
  };
  struct Word {};

  SUM_NS(suffix_op) {
    // typedef Token Nullary;
    struct Unary {
      Token op;
      Word arg_word;
    };
  }

  SCHEMA(
    data Token(Id id, Str val);

    enum suffix_op {
      Nullary %Token
    | Unary(Token op, Word arg_word)
    }

    // I guess we retain * for reference semantics and so forth
    // *out = val; can be useful

    data Other(Word[] words, Dict<Str, Word>* mydict, Str? option);

    // List<Word>* is also possible, but a bit verbose
    // Word words[] would be more like C++
    //
    // Probably want something more clearly different like:
    //
    // Word... words
    // [Word] words   -- synonym for List<Word>* words
    // Word@ words    -- not bad, for repetition
    //
    // There are also grammars with + and [] though
  );

  printf("Sum types defined");

  PASS();
}

namespace runtime_asdl {

class lvalue_t {};

class lvalue__Named : public lvalue_t {};

class lvalue__Indexed : public lvalue_t {};

#if 0
namespace lvalue {
  typedef lvalue__Named Named;
  typedef lvalue__Indexed Indexed;
}
#endif

// A CLASS can substitute for a namespace, but it can be "imported" with "using"
struct lvalue {
#if 0
  class Named: public lvalue_t {
  };
  class Indexed: public lvalue_t {
  };
#endif

  // typedef lvalue__Named Named;
  // typedef lvalue__Indexed Indexed;
  using Named = lvalue__Named;
  using Indexed = lvalue__Indexed;
};

};  // namespace runtime_asdl

namespace hnode_asdl {
#if 0
namespace hnode_e {
  const int Record = 1;
  const int Array = 2;
  const int Leaf = 3;
  const int External = 4;
};
#endif

// Not enum class, a namespace
struct hnode_e {
#if 0
  static const int Record = 1;
  static const int Array = 2;
  static const int Leaf = 3;
  static const int External = 4;
#endif
  enum no_name {
    Record = 1,
    Array = 2,
    Leaf = 3,
    External = 4,
  };
};

struct scope_e {
  enum no_name {
    Record = 1,
    Array = 2,
    Leaf = 3,
    External = 4,
  };
};

enum Other {
  Record = 2,
};

};  // namespace hnode_asdl

using hnode_asdl::hnode_e;
using runtime_asdl::lvalue;
// namespace lvalue = runtime_asdl::lvalue;

TEST asdl_namespace_demo() {
  lvalue::Named n;
  lvalue::Indexed i;

  (void)n;
  (void)i;

  log("Record = %d", hnode_e::Record);
  log("Array = %d", hnode_e::Array);

  // In Python, it's lvalue.Named(), not lvalue__Named
  //
  // Although you could change that everywhere
  //
  // from _devbuild.gen.runtime_asdl import lvalue
  //
  // can you reverse it?

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(typed_arith_parse::namespace_demo);

  RUN_TEST(test_misc);
  RUN_TEST(map_demo);
  RUN_TEST(shared_ptr_demo);
  RUN_TEST(template_demo);
  RUN_TEST(default_args_demo);
  RUN_TEST(sizeof_demo);
  RUN_TEST(except_demo);
  RUN_TEST(static_literals);
  RUN_TEST(enum_demo);
  RUN_TEST(field_mask_demo);
  // RUN_TEST(smartptr_inheritance_demo);

  RUN_TEST(mmap_demo);
  RUN_TEST(comma_demo);
  RUN_TEST(signed_unsigned_demo);
  RUN_TEST(param_passing_demo);

  RUN_TEST(tea_macros_demo);

  RUN_TEST(asdl_namespace_demo);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
