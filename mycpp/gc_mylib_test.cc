#include "gc_mylib.h"

#include "vendor/greatest.h"

TEST split_once_test() {
  log("split_once()");

  Str* s = nullptr;
  Str* delim = nullptr;
  StackRoots _roots1({&s, &delim});

  s = StrFromC("foo=bar");
  delim = StrFromC("=");
  Tuple2<Str*, Str*> t = mylib::split_once(s, delim);

  auto t0 = t.at0();
  auto t1 = t.at1();

  log("t %p %p", t0, t1);

  Str* foo = nullptr;
  StackRoots _roots2({&t0, &t1, &foo});
  foo = StrFromC("foo");

  PASS();

  Tuple2<Str*, Str*> u = mylib::split_once(StrFromC("foo="), StrFromC("="));
  ASSERT(str_equals(u.at0(), StrFromC("foo")));
  ASSERT(str_equals(u.at1(), StrFromC("")));

  Tuple2<Str*, Str*> v = mylib::split_once(StrFromC("foo="), StrFromC("Z"));
  ASSERT(str_equals(v.at0(), StrFromC("foo=")));
  ASSERT(v.at1() == nullptr);

  Tuple2<Str*, Str*> w = mylib::split_once(StrFromC(""), StrFromC("Z"));
  ASSERT(str_equals(w.at0(), StrFromC("")));
  ASSERT(w.at1() == nullptr);

  PASS();
}

TEST int_to_str_test() {
  int int_min = INT_MIN;
  Str* int_str;

  int_str = mylib::hex_lower(15);
  ASSERT(str_equals0("f", int_str));
  print(int_str);
  print(mylib::hex_lower(int_min));

  int_str = mylib::hex_upper(15);
  ASSERT(str_equals0("F", int_str));
  print(mylib::hex_upper(int_min));

  int_str = mylib::octal(15);
  ASSERT(str_equals0("17", int_str));
  print(mylib::octal(int_min));

  PASS();
}

TEST writer_test() {
  // Demonstrate bug with inheritance
  log("obj obj_len %d", offsetof(Obj, obj_len_));
  log("buf obj_len %d", offsetof(mylib::BufWriter, obj_len_));

  PASS();
}

using mylib::BufLineReader;

TEST buf_line_reader_test() {
  Str* s = nullptr;
  BufLineReader* reader = nullptr;
  Str* line = nullptr;

  StackRoots _roots({&s, &reader, &line});

  s = StrFromC("foo\nbar\nleftover");
  reader = Alloc<BufLineReader>(s);

  log("BufLineReader");

  line = reader->readline();
  log("1 [%s]", line->data_);
  ASSERT(str_equals0("foo\n", line));

  line = reader->readline();
  log("2 [%s]", line->data_);
  ASSERT(str_equals0("bar\n", line));

  line = reader->readline();
  log("3 [%s]", line->data_);
  ASSERT(str_equals0("leftover", line));

  line = reader->readline();
  log("4 [%s]", line->data_);
  ASSERT(str_equals0("", line));

  PASS();
}

TEST files_test() {
  mylib::Writer* stdout_ = mylib::Stdout();
  log("stdout isatty() = %d", stdout_->isatty());

  mylib::LineReader* stdin_ = mylib::Stdin();
  log("stdin isatty() = %d", stdin_->isatty());

  ASSERT_EQ(0, stdin_->fileno());

  FILE* f = fopen("README.md", "r");

  mylib::CFileLineReader* r = nullptr;
  Str* filename = nullptr;
  Str* filename2 = nullptr;
  StackRoots _roots({&r, &filename, &filename2});

  r = Alloc<mylib::CFileLineReader>(f);
  filename = StrFromC("README.md");
  filename2 = StrFromC("README.md ");
  // auto r = mylib::Stdin();

  log("files_test");
  int i = 0;
  while (true) {
    Str* s = r->readline();
    if (len(s) == 0) {
      break;
    }
    if (i < 5) {
      println_stderr(s);
    }
    ++i;
  };
  log("files_test DONE");

  auto f2 = mylib::open(filename);
  ASSERT(f2 != nullptr);

  // See if we can strip a space and still open it.  Underlying fopen() call
  // works.
  auto f3 = mylib::open(filename2->strip());
  ASSERT(f3 != nullptr);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init(1 << 20);

  GREATEST_MAIN_BEGIN();

  RUN_TEST(split_once_test);
  RUN_TEST(int_to_str_test);
  RUN_TEST(writer_test);

  RUN_TEST(buf_line_reader_test);
  RUN_TEST(files_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
