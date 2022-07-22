// clang-format off
#include "mycpp/myerror.h" // must come first because of 'errno' issue
// clang-format on

#include <errno.h>
#include <fcntl.h>  // O_RDWR

#include "_build/cpp/runtime_asdl.h"  // cell, etc
#include "_devbuild/gen/id.h"
#include "leaky_core.h"  // Chdir
#include "leaky_core_error.h"
#include "leaky_core_pyerror.h"
#include "leaky_frontend_match.h"
#include "leaky_libc.h"
#include "leaky_osh.h"
#include "leaky_pylib.h"
#include "leaky_stdlib.h"
#include "vendor/greatest.h"

namespace Id = id_kind_asdl::Id;

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

TEST match_test() {
  match::SimpleLexer* lex = match::BraceRangeLexer(new Str("{-1..22}"));

  while (true) {
    auto t = lex->Next();
    int id = t.at0();
    if (id == id__Eol_Tok) {
      break;
    }
    log("id = %d", id);
    log("val = %s", t.at1()->data_);
  }

  // BUG: cstring-TODO: Truncated string causes read past len_
  // Need a length check!
#if 0
  match::SimpleLexer* lex2 = match::BraceRangeLexer(new Str("1234", 2));
  while (true) {
    auto t = lex2->Next();
    int id = t.at0();
    if (id == id__Eol_Tok) {
      break;
    }
    log("id = %d", id);
    log("val = %s", t.at1()->data_);
  }
#endif

  ASSERT_EQ(Id::BoolUnary_G, match::BracketUnary(new Str("-G")));
  ASSERT_EQ(Id::Undefined_Tok, match::BracketUnary(new Str("-Gz")));
  ASSERT_EQ(Id::Undefined_Tok, match::BracketUnary(new Str("")));

  ASSERT_EQ(Id::BoolBinary_NEqual, match::BracketBinary(new Str("!=")));
  ASSERT_EQ(Id::Undefined_Tok, match::BracketBinary(new Str("")));

  // This still works, but can't it overflow a buffer?
  Str* s = new Str("!= ");
  Str* stripped = s->strip();

  ASSERT_EQ(3, len(s));
  ASSERT_EQ(2, len(stripped));

  ASSERT_EQ(Id::BoolBinary_NEqual, match::BracketBinary(stripped));

  PASS();
}

TEST util_test() {
  // OK this seems to work
  Str* escaped = pyutil::BackslashEscape(new Str("'foo bar'"), new Str(" '"));
  ASSERT(str_equals(escaped, new Str("\\'foo\\ bar\\'")));

  Str* escaped2 = pyutil::BackslashEscape(new Str(""), new Str(" '"));
  ASSERT(str_equals(escaped2, new Str("")));

  Str* s = pyutil::ChArrayToString(new List<int>({65}));
  ASSERT(str_equals(s, new Str("A")));
  ASSERT_EQ_FMT(1, len(s), "%d");

  Str* s2 = pyutil::ChArrayToString(new List<int>({102, 111, 111}));
  ASSERT(str_equals(s2, new Str("foo")));
  ASSERT_EQ_FMT(3, len(s2), "%d");

  Str* s3 = pyutil::ChArrayToString(new List<int>({45, 206, 188, 45}));
  ASSERT(str_equals(s3, new Str("-\xce\xbc-")));  // mu char
  ASSERT_EQ_FMT(4, len(s3), "%d");

  PASS();
}

TEST libc_test() {
  Str* s1 = (new Str("foo.py "))->strip();
  ASSERT(libc::fnmatch(new Str("*.py"), s1));
  ASSERT(!libc::fnmatch(new Str("*.py"), new Str("foo.p")));

  // extended glob
  ASSERT(libc::fnmatch(new Str("*(foo|bar).py"), new Str("foo.py")));
  ASSERT(!libc::fnmatch(new Str("*(foo|bar).py"), new Str("foo.p")));

  List<Str*>* results =
      libc::regex_match(new Str("(a+).(a+)"), new Str("-abaacaaa"));
  ASSERT_EQ_FMT(3, len(results), "%d");
  ASSERT(str_equals(new Str("abaa"), results->index_(0)));  // whole match
  ASSERT(str_equals(new Str("a"), results->index_(1)));
  ASSERT(str_equals(new Str("aa"), results->index_(2)));

  results = libc::regex_match(new Str("z+"), new Str("abaacaaa"));
  ASSERT_EQ(nullptr, results);

  Tuple2<int, int>* result;
  Str* s = new Str("oXooXoooXoX");
  result = libc::regex_first_group_match(new Str("(X.)"), s, 0);
  ASSERT_EQ_FMT(1, result->at0(), "%d");
  ASSERT_EQ_FMT(3, result->at1(), "%d");

  result = libc::regex_first_group_match(new Str("(X.)"), s, 3);
  ASSERT_EQ_FMT(4, result->at0(), "%d");
  ASSERT_EQ_FMT(6, result->at1(), "%d");

  result = libc::regex_first_group_match(new Str("(X.)"), s, 6);
  ASSERT_EQ_FMT(8, result->at0(), "%d");
  ASSERT_EQ_FMT(10, result->at1(), "%d");

  // This depends on the file system
  auto files = libc::glob(new Str("*.md"));
  ASSERT_EQ_FMT(1, len(files), "%d");
  print(files->index_(0));  // should get README.md only

  auto files2 = libc::glob(new Str("*.pyzzz"));
  ASSERT_EQ_FMT(0, len(files2), "%d");

  Str* h = libc::gethostname();
  log("gethostname() =");
  print(h);

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
  log("getcwd() =");
  print(cwd);

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
    e_strict(new Str("foo"));
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
    bool_stat::isatty(new Str("invalid"), nullptr);
  } catch (error::FatalRuntime* e) {
    fail++;
  }
  ASSERT_EQ(1, fail);

  bool b2 = bool_stat::isatty(new Str("0"), nullptr);
  // This will be true interactively
  log("stdin isatty = %d", b2);

  PASS();
}

TEST pyos_readbyte_test() {
  // Write 2 bytes to this file
  const char* tmp_name = "_tmp/pyos_ReadByte";
  int fd = ::open(tmp_name, O_CREAT | O_RDWR, 0644);
  if (fd < 0) {
    printf("1. ERROR %s", strerror(errno));
  }
  ASSERT(fd > 0);
  write(fd, "SH", 2);
  close(fd);

  fd = ::open(tmp_name, O_CREAT | O_RDWR, 0644);
  if (fd < 0) {
    printf("2. ERROR %s", strerror(errno));
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
  const char* tmp_name = "_tmp/pyos_Read";
  int fd = ::open(tmp_name, O_CREAT | O_RDWR, 0644);
  if (fd < 0) {
    printf("1. ERROR %s", strerror(errno));
  }
  ASSERT(fd > 0);
  write(fd, "SH", 2);
  close(fd);

  // open needs an absolute path for some reason?  _tmp/pyos doesn't work
  fd = ::open(tmp_name, O_CREAT | O_RDWR, 0644);
  if (fd < 0) {
    printf("2. ERROR %s", strerror(errno));
  }

  List<Str*>* chunks = new List<Str*>();
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
  // TODO: use gc_mylib here, with AllocStr(), StackRoots, etc.
  Str* s = nullptr;

  s = os_path::rstrip_slashes(new Str(""));
  ASSERT(str_equals(s, new Str("")));

  s = os_path::rstrip_slashes(new Str("foo"));
  ASSERT(str_equals(s, new Str("foo")));

  s = os_path::rstrip_slashes(new Str("foo/"));
  ASSERT(str_equals(s, new Str("foo")));

  s = os_path::rstrip_slashes(new Str("/foo/"));
  ASSERT(str_equals(s, new Str("/foo")));

  // special case of not stripping
  s = os_path::rstrip_slashes(new Str("///"));
  ASSERT(str_equals(s, new Str("///")));

  PASS();
}

TEST putenv_test() {
  Str* key = new Str("KEY");
  Str* value = new Str("value");

  posix::putenv(key, value);
  char* got_value = ::getenv(key->data());
  ASSERT(got_value && str_equals(new Str(got_value), value));

  PASS();
}

TEST pyos_test() {
  // This test isn't hermetic but it should work in most places, including in a
  // container
  int err_num = pyos::Chdir(new Str("/"));
  ASSERT(err_num == 0);

  err_num = pyos::Chdir(new Str("/nonexistent__"));
  ASSERT(err_num != 0);

  Dict<Str*, Str*>* env = pyos::Environ();
  Str* p = env->get(new Str("PATH"));
  ASSERT(p != nullptr);
  log("PATH = %s", p->data_);

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  // TODO: use garbage collection in this test?

  GREATEST_MAIN_BEGIN();

  RUN_TEST(show_sizeof);
  RUN_TEST(match_test);
  RUN_TEST(util_test);
  RUN_TEST(libc_test);
  RUN_TEST(time_test);
  RUN_TEST(posix_test);
  RUN_TEST(exceptions);
  RUN_TEST(bool_stat_test);
  RUN_TEST(pyos_readbyte_test);
  RUN_TEST(pyos_read_test);
  RUN_TEST(os_path_test);
  RUN_TEST(putenv_test);

  // Disabled because changing the dir somehow prevents the
  // leaky_binding_test.profraw file from being created
  //
  // Must come last because it does chdir()
  //
  // RUN_TEST(pyos_test);

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
