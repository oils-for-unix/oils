#include "cpp/core.h"

#include <errno.h>        // errno
#include <fcntl.h>        // O_RDWR
#include <signal.h>       // SIG*, kill()
#include <sys/stat.h>     // stat
#include <sys/utsname.h>  // uname
#include <sys/wait.h>     // waitpid
#include <unistd.h>       // getpid(), getuid(), environ

#include "cpp/embedded_file.h"
#include "cpp/stdlib.h"         // posix::getcwd
#include "mycpp/gc_builtins.h"  // IOError_OSError
#include "vendor/greatest.h"

TEST for_test_coverage() {
  pyos::FlushStdout();

  PASS();
}

GLOBAL_STR(v1, "v1");
GLOBAL_STR(v2, "v2");

TextFile gTmp[] = {
    {.rel_path = "k1", .contents = v1},
    {.rel_path = "k2", .contents = v2},
    {.rel_path = nullptr, .contents = nullptr},
};

TextFile* gEmbeddedFiles = gTmp;  // turn array into pointer

TEST loader_test() {
  auto loader = pyutil::GetResourceLoader();

  BigStr* version = pyutil::GetVersion(loader);
  ASSERT(len(version) > 3);

  pyutil::PrintVersionDetails(loader);

  ASSERT_EQ(v1, loader->Get(StrFromC("k1")));
  ASSERT_EQ(v2, loader->Get(StrFromC("k2")));

  bool caught = false;
  try {
    loader->Get(kEmptyString);
  } catch (IOError*) {
    caught = true;
  }
  ASSERT(caught);

  PASS();
}

TEST exceptions_test() {
  bool caught = false;
  try {
    throw Alloc<pyos::ReadError>(0);
  } catch (pyos::ReadError* e) {
    log("e %p", e);
    caught = true;
  }

  ASSERT(caught);

  PASS();
}

TEST environ_test() {
  Dict<BigStr*, BigStr*>* env = pyos::Environ();
  BigStr* p = env->get(StrFromC("PATH"));
  ASSERT(p != nullptr);
  log("PATH = %s", p->data_);

  PASS();
}

TEST user_home_dir_test() {
  uid_t uid = getuid();
  BigStr* username = pyos::GetUserName(uid);
  ASSERT(username != nullptr);

  BigStr* dir0 = pyos::GetMyHomeDir();
  ASSERT(dir0 != nullptr);

  BigStr* dir1 = pyos::GetHomeDir(username);
  ASSERT(dir1 != nullptr);

  ASSERT(str_equals(dir0, dir1));

  PASS();
}

TEST uname_test() {
  BigStr* os_type = pyos::OsType();
  ASSERT(os_type != nullptr);

  utsname un = {};
  ASSERT(uname(&un) == 0);
  ASSERT(str_equals(StrFromC(un.sysname), os_type));

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

  List<BigStr*>* chunks = NewList<BigStr*>();
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
  Tuple3<double, double, double> t = pyos::Time();
  ASSERT(t.at0() > 0.0);
  ASSERT(t.at1() >= 0.0);
  ASSERT(t.at2() >= 0.0);

  Tuple2<int, int> result = pyos::WaitPid(0);
  ASSERT_EQ(-1, result.at0());  // no children to wait on

  // This test isn't hermetic but it should work in most places, including in a
  // container

  BigStr* current = posix::getcwd();

  int err_num = pyos::Chdir(StrFromC("/"));
  ASSERT(err_num == 0);

  err_num = pyos::Chdir(StrFromC("/nonexistent__"));
  ASSERT(err_num != 0);

  err_num = pyos::Chdir(current);
  ASSERT(err_num == 0);

  PASS();
}

TEST pyutil_test() {
  ASSERT_EQ(true, pyutil::IsValidCharEscape(StrFromC("#")));
  ASSERT_EQ(false, pyutil::IsValidCharEscape(StrFromC("a")));

  // OK this seems to work
  BigStr* escaped =
      pyutil::BackslashEscape(StrFromC("'foo bar'"), StrFromC(" '"));
  ASSERT(str_equals(escaped, StrFromC("\\'foo\\ bar\\'")));

  BigStr* escaped2 = pyutil::BackslashEscape(StrFromC(""), StrFromC(" '"));
  ASSERT(str_equals(escaped2, StrFromC("")));

  BigStr* s = pyutil::ChArrayToString(NewList<int>({65}));
  ASSERT(str_equals(s, StrFromC("A")));
  ASSERT_EQ_FMT(1, len(s), "%d");

  BigStr* s2 = pyutil::ChArrayToString(NewList<int>({102, 111, 111}));
  ASSERT(str_equals(s2, StrFromC("foo")));
  ASSERT_EQ_FMT(3, len(s2), "%d");

  BigStr* s3 = pyutil::ChArrayToString(NewList<int>({45, 206, 188, 45}));
  ASSERT(str_equals(s3, StrFromC("-\xce\xbc-")));  // mu char
  ASSERT_EQ_FMT(4, len(s3), "%d");

  pyos::PrintTimes();

  PASS();
}

TEST strerror_test() {
  IOError_OSError err(EINVAL);
  BigStr* s1 = pyutil::strerror(&err);
  ASSERT(s1 != nullptr);

  BigStr* s2 = StrFromC(strerror(EINVAL));
  ASSERT(s2 != nullptr);

  ASSERT(str_equals(s1, s2));

  PASS();
}

TEST signal_test() {
  pyos::SignalSafe* signal_safe = pyos::InitSignalSafe();

  {
    List<int>* q = signal_safe->TakePendingSignals();
    ASSERT(q != nullptr);
    ASSERT_EQ(0, len(q));
    signal_safe->ReuseEmptyList(q);
  }

  pid_t mypid = getpid();

  pyos::RegisterSignalInterest(SIGUSR1);
  pyos::RegisterSignalInterest(SIGUSR2);

  kill(mypid, SIGUSR1);
  ASSERT_EQ(SIGUSR1, signal_safe->LastSignal());

  kill(mypid, SIGUSR2);
  ASSERT_EQ(SIGUSR2, signal_safe->LastSignal());

  {
    List<int>* q = signal_safe->TakePendingSignals();
    ASSERT(q != nullptr);
    ASSERT_EQ(2, len(q));
    ASSERT_EQ(SIGUSR1, q->at(0));
    ASSERT_EQ(SIGUSR2, q->at(1));

    q->clear();
    signal_safe->ReuseEmptyList(q);
  }

  pyos::sigaction(SIGUSR1, SIG_IGN);
  kill(mypid, SIGUSR1);
  {
    List<int>* q = signal_safe->TakePendingSignals();
    ASSERT(q != nullptr);
    ASSERT(len(q) == 0);
    signal_safe->ReuseEmptyList(q);
  }
  pyos::sigaction(SIGUSR2, SIG_IGN);

  pyos::RegisterSignalInterest(SIGWINCH);

  kill(mypid, SIGWINCH);
  ASSERT_EQ(pyos::UNTRAPPED_SIGWINCH, signal_safe->LastSignal());

  signal_safe->SetSigWinchCode(SIGWINCH);

  kill(mypid, SIGWINCH);
  ASSERT_EQ(SIGWINCH, signal_safe->LastSignal());
  {
    List<int>* q = signal_safe->TakePendingSignals();
    ASSERT(q != nullptr);
    ASSERT_EQ(2, len(q));
    ASSERT_EQ(SIGWINCH, q->at(0));
    ASSERT_EQ(SIGWINCH, q->at(1));
  }

  PASS();
}

TEST signal_safe_test() {
  pyos::SignalSafe signal_safe;

  List<int>* received = signal_safe.TakePendingSignals();

  // We got now signals
  ASSERT_EQ_FMT(0, len(received), "%d");

  // The existing queue is of length 0
  ASSERT_EQ_FMT(0, len(signal_safe.pending_signals_), "%d");

  // Capacity is a ROUND NUMBER from the allocator's POV
  // There's no convenient way to test the obj_len we pass to gHeap.Allocate,
  // but it should be (1022 + 2) * 4.
  ASSERT_EQ_FMT(1022, signal_safe.pending_signals_->capacity_, "%d");

  // Register too many signals
  for (int i = 0; i < pyos::kMaxPendingSignals + 10; ++i) {
    signal_safe.UpdateFromSignalHandler(SIGINT);
  }

  PASS();
}

TEST passwd_test() {
  uid_t my_uid = getuid();
  BigStr* username = pyos::GetUserName(my_uid);
  ASSERT(username != nullptr);

  List<pyos::PasswdEntry*>* entries = pyos::GetAllUsers();
  if (len(entries) == 0) {
    fprintf(stderr, "No *pwent() functions, skipping tests\n");
    PASS();
  }

  pyos::PasswdEntry* me = nullptr;
  for (ListIter<pyos::PasswdEntry*> it(entries); !it.Done(); it.Next()) {
    pyos::PasswdEntry* entry = it.Value();
    if (entry->pw_uid == static_cast<int>(my_uid)) {
      me = entry;
      break;
    }
  }
  ASSERT(me != nullptr);
  ASSERT(me->pw_name != nullptr);
  ASSERT(str_equals(username, me->pw_name));

  PASS();
}

TEST dir_cache_key_test() {
  struct stat st;
  ASSERT(::stat("/", &st) == 0);

  Tuple2<BigStr*, int>* key = pyos::MakeDirCacheKey(StrFromC("/"));
  ASSERT(str_equals(key->at0(), StrFromC("/")));
  ASSERT(key->at1() == st.st_mtime);

  int ec = -1;
  try {
    pyos::MakeDirCacheKey(StrFromC("nonexistent_ZZ"));
  } catch (IOError_OSError* e) {
    ec = e->errno_;
  }
  ASSERT(ec == ENOENT);

  PASS();
}

// Test the theory that LeakSanitizer tests for reachability from global
// variables.
struct Node {
  Node* next;
};
Node* gNode;

TEST asan_global_leak_test() {
  // NOT reported as a leak
  gNode = static_cast<Node*>(malloc(sizeof(Node)));
  gNode->next = static_cast<Node*>(malloc(sizeof(Node)));

  // Turn this on and ASAN will report a leak!
  if (0) {
    free(gNode);
  }
  PASS();
}

// manual demo
TEST waitpid_demo() {
  pyos::InitSignalSafe();
  pyos::RegisterSignalInterest(SIGINT);

  int result = fork();
  if (result < 0) {
    FAIL();
  } else if (result == 0) {
    // child

    log("sleeping in child, pid = %d", getpid());
    char* argv[] = {"sleep", "5", nullptr};
    char* env[] = {nullptr};
    int e = execvpe("sleep", argv, env);
    log("execve failed %d", e);

  } else {
    // parent

    int wstatus;
    log("waiting in parent");
    int result = ::waitpid(-1, &wstatus, 0);
    log("waitpid = %d, status = %d", result, wstatus);
  }

  PASS();
}

GREATEST_MAIN_DEFS();

int main(int argc, char** argv) {
  gHeap.Init();

  GREATEST_MAIN_BEGIN();

  RUN_TEST(for_test_coverage);
  RUN_TEST(loader_test);
  RUN_TEST(exceptions_test);
  RUN_TEST(environ_test);
  RUN_TEST(user_home_dir_test);
  RUN_TEST(uname_test);
  RUN_TEST(pyos_readbyte_test);
  RUN_TEST(pyos_read_test);
  RUN_TEST(pyos_test);  // non-hermetic
  RUN_TEST(pyutil_test);
  RUN_TEST(strerror_test);

  RUN_TEST(signal_test);
  RUN_TEST(signal_safe_test);

  RUN_TEST(passwd_test);
  RUN_TEST(dir_cache_key_test);
  RUN_TEST(asan_global_leak_test);

  // RUN_TEST(waitpid_demo);

  gHeap.CleanProcessExit();

  GREATEST_MAIN_END(); /* display results */
  return 0;
}
