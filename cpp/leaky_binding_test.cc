
#include <errno.h>
#include <fcntl.h>  // O_RDWR

#include "_gen/core/runtime.asdl.h"  // cell, etc
#include "leaky_core.h"  // Chdir
#include "leaky_core_error.h"
#include "leaky_core_pyerror.h"
#include "leaky_libc.h"
#include "leaky_osh.h"
#include "leaky_pylib.h"
#include "leaky_stdlib.h"
#include "mycpp/builtins.h"
#include "vendor/greatest.h"

TEST show_sizeof() {
  // Without sed hack, it's 24 bytes because we have tag (2), id (4), val,
  // span_id.
  // Now 16 bytes.
  log("sizeof(Token) = %d", sizeof(syntax_asdl::Token));
  log("alignof(Token) = %d", alignof(syntax_asdl::Token));
  log("alignof(Token*) = %d", alignof(syntax_asdl::Token*));

  // Without sed hack, it's 12 bytes for tag (2) id (4) and span_id (4).
  // Now 8 bytes.
  log("sizeof(speck) = %d", sizeof(syntax_asdl::speck));

  // 16 bytes: 2 byte tag + 3 integer fields
  log("sizeof(line_span) = %d", sizeof(syntax_asdl::line_span));

  // Reordered to be 16 bytes
  log("sizeof(cell) = %d", sizeof(runtime_asdl::cell));

  // 24 bytes: std::vector
  log("sizeof(List<int>) = %d", sizeof(List<int>));
  log("sizeof(List<Str*>) = %d", sizeof(List<Str*>));

  // Unlike Python, this is -1, not 255!
  int mod = -1 % 256;
  log("mod = %d", mod);

  log("alignof(bool) = %d", alignof(bool));
  log("alignof(int) = %d", alignof(int));
  log("alignof(float) = %d", alignof(float));

  log("sizeof(Str) = %d", sizeof(Str));
  log("alignof(Str) = %d", alignof(Str));

  log("sizeof(Str*) = %d", sizeof(Str*));
  log("alignof(Str*) = %d", alignof(Str*));

  log("alignof(max_align_t) = %d", alignof(max_align_t));

  PASS();
}

TEST util_test() {
  // OK this seems to work
  Str* escaped = pyutil::BackslashEscape(StrFromC("'foo bar'"), StrFromC(" '"));
  ASSERT(str_equals(escaped, StrFromC("\\'foo\\ bar\\'")));

  Str* escaped2 = pyutil::BackslashEscape(StrFromC(""), StrFromC(" '"));
  ASSERT(str_equals(escaped2, StrFromC("")));

  Str* s = pyutil::ChArrayToString(NewList<int>({65}));
  ASSERT(str_equals(s, StrFromC("A")));
  ASSERT_EQ_FMT(1, len(s), "%d");

  Str* s2 = pyutil::ChArrayToString(NewList<int>({102, 111, 111}));
  ASSERT(str_equals(s2, StrFromC("foo")));
  ASSERT_EQ_FMT(3, len(s2), "%d");

  Str* s3 = pyutil::ChArrayToString(NewList<int>({45, 206, 188, 45}));
  ASSERT(str_equals(s3, StrFromC("-\xce\xbc-")));  // mu char
  ASSERT_EQ_FMT(4, len(s3), "%d");

  PASS();
}

TEST libc_test() {
  Str* s1 = (StrFromC("foo.py "))->strip();
  ASSERT(libc::fnmatch(StrFromC("*.py"), s1));
  ASSERT(!libc::fnmatch(StrFromC("*.py"), StrFromC("foo.p")));

  // extended glob
  ASSERT(libc::fnmatch(StrFromC("*(foo|bar).py"), StrFromC("foo.py")));
  ASSERT(!libc::fnmatch(StrFromC("*(foo|bar).py"), StrFromC("foo.p")));

  List<Str*>* results =
      libc::regex_match(StrFromC("(a+).(a+)"), StrFromC("-abaacaaa"));
  ASSERT_EQ_FMT(3, len(results), "%d");
  ASSERT(str_equals(StrFromC("abaa"), results->index_(0)));  // whole match
  ASSERT(str_equals(StrFromC("a"), results->index_(1)));
  ASSERT(str_equals(StrFromC("aa"), results->index_(2)));

  results = libc::regex_match(StrFromC("z+"), StrFromC("abaacaaa"));
  ASSERT_EQ(nullptr, results);

  Tuple2<int, int>* result;
  Str* s = StrFromC("oXooXoooXoX");
  result = libc::regex_first_group_match(StrFromC("(X.)"), s, 0);
  ASSERT_EQ_FMT(1, result->at0(), "%d");
  ASSERT_EQ_FMT(3, result->at1(), "%d");

  result = libc::regex_first_group_match(StrFromC("(X.)"), s, 3);
  ASSERT_EQ_FMT(4, result->at0(), "%d");
  ASSERT_EQ_FMT(6, result->at1(), "%d");

  result = libc::regex_first_group_match(StrFromC("(X.)"), s, 6);
  ASSERT_EQ_FMT(8, result->at0(), "%d");
  ASSERT_EQ_FMT(10, result->at1(), "%d");

  Str* h = libc::gethostname();
  log("gethostname() = %s %d", h->data_, len(h));

  PASS();
}

TEST time_test() {
  int ts = time_::time();
  log("ts = %d", ts);
  ASSERT(ts > 0);
  PASS();
}

TEST posix_test() {
  Str* cwd = posix::getcwd();
  log("getcwd() = %s %d", cwd->data_, len(cwd));

  Str* message = posix::strerror(EBADF);
  log("strerror");
  print(message);

  PASS();
}

// HACK!  asdl/runtime.py isn't translated, but leaky_core_error.h uses it...
namespace runtime {
int NO_SPID = -1;
};

TEST exceptions() {
  bool caught = false;
  try {
    e_strict(StrFromC("foo"));
  } catch (error::Strict* e) {  // Catch by reference!
    // log("%p ", e);
    caught = true;
  }
  ASSERT(caught);

  PASS();
}

TEST bool_stat_test() {
  int fail = 0;
  try {
    bool_stat::isatty(StrFromC("invalid"), nullptr);
  } catch (error::FatalRuntime* e) {
    fail++;
  }
  ASSERT_EQ(1, fail);

  bool b2 = bool_stat::isatty(StrFromC("0"), nullptr);
  // This will be true interactively
  log("stdin isatty = %d", b2);

  PASS();
}

TEST pyos_readbyte_test() {
  // Write 2 bytes to this file
  const char* tmp_name = "pyos_ReadByte";
  int fd = ::open(tmp_name, O_CREAT | O_RDWR, 0644);
  if (fd < 0) {
    printf("1. ERROR %s\n", strerror(errno));
  }
  ASSERT(fd > 0);
  write(fd, "SH", 2);
  close(fd);

  fd = ::open(tmp_name, O_CREAT | O_RDWR, 0644);
  if (fd < 0) {
    printf("2. ERROR %s\n", strerror(errno));
  }

  Tuple2<int, int> tup = pyos::ReadByte(fd);
  ASSERT_EQ_FMT(0, tup.at1(), "%d");  // error code
  ASSERT_EQ_FMT('S', tup.at0(), "%d");

  tup = pyos::ReadByte(fd);
  ASSERT_EQ_FMT(0, tup.at1(), "%d");  // error code
  ASSERT_EQ_FMT('H', tup.at0(), "%d");

  tup = pyos::ReadByte(fd);
  ASSERT_EQ_FMT(0, tup.at1(), "%d");  // error code
  ASSERT_EQ_FMT(pyos::EOF_SENTINEL, tup.at0(), "%d");

  close(fd);

  PASS();
}

TEST pyos_read_test() {
  const char* tmp_name = "pyos_Read";
  int fd = ::open(tmp_name, O_CREAT | O_RDWR, 0644);
  if (fd < 0) {
    printf("3. ERROR %s\n", strerror(errno));
  }
  ASSERT(fd > 0);
  write(fd, "SH", 2);
  close(fd);

  // open needs an absolute path for some reason?  _tmp/pyos doesn't work
  fd = ::open(tmp_name, O_CREAT | O_RDWR, 0644);
  if (fd < 0) {
    printf("4. ERROR %s\n", strerror(errno));
  }

  List<Str*>* chunks = NewList<Str*>();
  Tuple2<int, int> tup = pyos::Read(fd, 4096, chunks);
  ASSERT_EQ_FMT(2, tup.at0(), "%d");  // error code
  ASSERT_EQ_FMT(0, tup.at1(), "%d");
  ASSERT_EQ_FMT(1, len(chunks), "%d");

  tup = pyos::Read(fd, 4096, chunks);
  ASSERT_EQ_FMT(0, tup.at0(), "%d");  // error code
  ASSERT_EQ_FMT(0, tup.at1(), "%d");
  ASSERT_EQ_FMT(1, len(chunks), "%d");

  close(fd);

  PASS();
}

TEST os_path_test() {
  // TODO: use gc_mylib here, with NewStr(), StackRoots, etc.
  Str* s = nullptr;

  s = os_path::rstrip_slashes(StrFromC(""));
  ASSERT(str_equals(s, StrFromC("")));

  s = os_path::rstrip_slashes(StrFromC("foo"));
  ASSERT(str_equals(s, StrFromC("foo")));

  s = os_path::rstrip_slashes(StrFromC("foo/"));
  ASSERT(str_equals(s, StrFromC("foo")));

  s = os_path::rstrip_slashes(StrFromC("/foo/"));
  ASSERT(str_equals(s, StrFromC("/foo")));

  // special case of not stripping
  s = os_path::rstrip_slashes(StrFromC("///"));
  ASSERT(str_equals(s, StrFromC("///")));

  PASS();
}

TEST putenv_test() {
  Str* key = StrFromC("KEY");
  Str* value = StrFromC("value");

  posix::putenv(key, value);
  char* got_value = ::getenv(key->data());
  ASSERT(got_value && str_equals(StrFromC(got_value), value));

  PASS();
}

TEST libc_glob_test() {
  // This depends on the file system
  auto files = libc::glob(StrFromC("*.testdata"));
  // 3 files are made by the shell wrapper
  ASSERT_EQ_FMT(3, len(files), "%d");

  print(files->index_(0));

  auto files2 = libc::glob(StrFromC("*.pyzzz"));
  ASSERT_EQ_FMT(0, len(files2), "%d");

  PASS();
}

TEST pyos_test() {
  // This test isn't hermetic but it should work in most places, including in a
  // container

  Str* current = posix::getcwd();

  int err_num = pyos::Chdir(StrFromC("/"));
  ASSERT(err_num == 0);

  err_num = pyos::Chdir(StrFromC("/nonexistent__"));
  ASSERT(err_num != 0);

  err_num = pyos::Chdir(current);
  ASSERT(err_num == 0);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(show_sizeof);
  RUN_TEST(util_test);
  RUN_TEST(libc_test);
  RUN_TEST(libc_glob_test);
  RUN_TEST(time_test);
  RUN_TEST(posix_test);
  RUN_TEST(exceptions);
  RUN_TEST(bool_stat_test);
  RUN_TEST(pyos_readbyte_test);
  RUN_TEST(pyos_read_test);
  RUN_TEST(os_path_test);
  RUN_TEST(putenv_test);

  // non-hermetic
  RUN_TEST(pyos_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
