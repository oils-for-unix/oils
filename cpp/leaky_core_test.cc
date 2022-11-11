#include "cpp/leaky_core.h"

#include <fcntl.h>  // O_RDWR

#include "cpp/leaky_core_error.h"    // error::Strict
#include "cpp/leaky_core_pyerror.h"  // e_strict
#include "cpp/leaky_stdlib.h"        // posix::getcwd
#include "vendor/greatest.h"

TEST environ_test() {
  Dict<Str*, Str*>* env = pyos::Environ();
  Str* p = env->get(StrFromC("PATH"));
  ASSERT(p != nullptr);
  log("PATH = %s", p->data_);

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

TEST pyutil_test() {
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

TEST exceptions_test() {
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

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(environ_test);

  RUN_TEST(pyos_readbyte_test);
  RUN_TEST(pyos_read_test);

  RUN_TEST(pyos_test);  // non-hermetic

  RUN_TEST(pyutil_test);

  RUN_TEST(exceptions_test);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
