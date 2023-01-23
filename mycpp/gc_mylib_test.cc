#include "mycpp/gc_mylib.h"

#include "mycpp/gc_alloc.h"  // gHeap
#include "mycpp/gc_str.h"
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

  // TODO: We lack rooting in the cases below!
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

TEST funcs_test() {
  Str* int_str = nullptr;

  StackRoots _roots({&int_str});

  Str* fooEqualsBar = nullptr;
  Str* foo = nullptr;
  Str* bar = nullptr;
  Str* fooEquals = nullptr;

  Str* equals = nullptr;
  Str* Z = nullptr;
  Str* emptyStr = nullptr;

  StackRoots _roots2(
      {&fooEqualsBar, &foo, &bar, &fooEquals, &equals, &Z, &emptyStr});

  fooEqualsBar = StrFromC("foo=bar");
  foo = StrFromC("foo");
  bar = StrFromC("bar");
  fooEquals = StrFromC("foo=");

  equals = StrFromC("=");
  Z = StrFromC("Z");
  emptyStr = StrFromC("");

  log("split_once()");
  Tuple2<Str*, Str*> t = mylib::split_once(fooEqualsBar, equals);
  ASSERT(str_equals(t.at0(), foo));
  ASSERT(str_equals(t.at1(), bar));

  Tuple2<Str*, Str*> u = mylib::split_once(fooEquals, equals);
  ASSERT(str_equals(u.at0(), foo));
  ASSERT(str_equals(u.at1(), emptyStr));

  Tuple2<Str*, Str*> v = mylib::split_once(fooEquals, Z);
  ASSERT(str_equals(v.at0(), fooEquals));
  ASSERT(v.at1() == nullptr);

  Tuple2<Str*, Str*> w = mylib::split_once(emptyStr, Z);
  ASSERT(str_equals(w.at0(), emptyStr));
  ASSERT(w.at1() == nullptr);

  PASS();
}

#if 0
TEST writeln_test() {
  mylib::writeln(StrFromC("stdout"));
  mylib::writeln(StrFromC("stderr"), mylib::kStderr);

  PASS();
}
#endif

TEST BufWriter_test() {
  mylib::BufWriter* writer = nullptr;
  Str* s = nullptr;
  Str* foo = nullptr;
  Str* bar = nullptr;
  StackRoots _roots({&writer, &s, &foo, &bar});

  foo = StrFromC("foo");
  bar = StrFromC("bar");

  writer = Alloc<mylib::BufWriter>();
  s = writer->getvalue();
  ASSERT_EQ(kEmptyString, s);

  // Create a new BufWriter to call getvalue() again
  writer = Alloc<mylib::BufWriter>();
  writer->write(foo);
  s = writer->getvalue();
  ASSERT(str_equals0("foo", s));

  // Create a new BufWriter to call getvalue() again
  writer = Alloc<mylib::BufWriter>();
  writer->write(foo);
  writer->write(bar);

  s = writer->getvalue();
  ASSERT(str_equals0("foobar", s));
  log("result = %s", s->data());

  PASS();
}

using mylib::BufLineReader;

TEST BufLineReader_test() {
  Str* s = nullptr;
  BufLineReader* reader = nullptr;
  Str* line = nullptr;

  StackRoots _roots({&s, &reader, &line});

  s = StrFromC("foo\nbar\nleftover");
  reader = Alloc<BufLineReader>(s);

  ASSERT_EQ(false, reader->isatty());

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

  reader->close();

  PASS();
}

TEST files_test() {
  mylib::Writer* stdout_ = mylib::Stdout();
  log("stdout isatty() = %d", stdout_->isatty());

  mylib::LineReader* stdin_ = mylib::Stdin();
  log("stdin isatty() = %d", stdin_->isatty());

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
      mylib::print_stderr(s);
    }
    ++i;
  }
  r->close();
  log("files_test DONE");

  auto f2 = mylib::open(filename);
  ASSERT(f2 != nullptr);

  // See if we can strip a space and still open it.  Underlying fopen() call
  // works.
  auto f3 = mylib::open(filename2->strip());
  ASSERT(f3 != nullptr);

  auto w = Alloc<mylib::CFileWriter>(stdout);
  w->write(StrFromC("stdout"));
  w->flush();

  PASS();
}

TEST for_test_coverage() {
  mylib::MaybeCollect();  // trivial wrapper for translation
  mylib::StrFromC("x");   // trivial wrapper for translation

  auto writer = mylib::Stderr();
  writer->write(kEmptyString);

  // Methods we're not really using?  Refactoring types could eliminate these
  auto w = Alloc<mylib::BufWriter>();
  ASSERT_EQ(false, w->isatty());
  w->flush();

  // Initializes the heap
  mylib::InitCppOnly();

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(split_once_test);
  RUN_TEST(int_to_str_test);
  RUN_TEST(funcs_test);

  // RUN_TEST(writeln_test);
  RUN_TEST(BufWriter_test);
  RUN_TEST(BufLineReader_test);
  RUN_TEST(files_test);
  RUN_TEST(for_test_coverage);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */

  return 0;
}
