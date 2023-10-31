// core.cc

#include "cpp/core.h"

#include <ctype.h>  // ispunct()
#include <errno.h>
#include <math.h>  // fmod()
#include <pwd.h>   // passwd
#include <signal.h>
#include <sys/resource.h>  // getrusage
#include <sys/select.h>    // select(), FD_ISSET, FD_SET, FD_ZERO
#include <sys/stat.h>      // stat
#include <sys/time.h>      // gettimeofday
#include <sys/times.h>     // tms / times()
#include <sys/utsname.h>   // uname
#include <sys/wait.h>      // waitpid()
#include <termios.h>       // tcgetattr(), tcsetattr()
#include <time.h>          // time()
#include <unistd.h>        // getuid(), environ

#include "_gen/cpp/build_stamp.h"  // gCommitHash
#include "_gen/frontend/consts.h"  // gVersion
#include "cpp/embedded_file.h"

extern char** environ;

namespace pyos {

SignalSafe* gSignalSafe = nullptr;

Tuple2<int, int> WaitPid(int waitpid_options) {
  int status;
  int result = ::waitpid(-1, &status, WUNTRACED | waitpid_options);
  if (result < 0) {
    if (errno == EINTR && gSignalSafe->PollSigInt()) {
      throw Alloc<KeyboardInterrupt>();
    }
    return Tuple2<int, int>(-1, errno);
  }
  return Tuple2<int, int>(result, status);
}

Tuple2<int, int> Read(int fd, int n, List<BigStr*>* chunks) {
  BigStr* s = OverAllocatedStr(n);  // Allocate enough for the result

  int length = ::read(fd, s->data(), n);
  if (length < 0) {
    if (errno == EINTR && gSignalSafe->PollSigInt()) {
      throw Alloc<KeyboardInterrupt>();
    }
    return Tuple2<int, int>(-1, errno);
  }
  if (length == 0) {
    return Tuple2<int, int>(length, 0);
  }

  // Now we know how much data we got back
  s->MaybeShrink(length);
  chunks->append(s);

  return Tuple2<int, int>(length, 0);
}

Tuple2<int, int> ReadByte(int fd) {
  unsigned char buf[1];
  ssize_t n = read(fd, &buf, 1);
  if (n < 0) {  // read error
    if (errno == EINTR && gSignalSafe->PollSigInt()) {
      throw Alloc<KeyboardInterrupt>();
    }
    return Tuple2<int, int>(-1, errno);
  } else if (n == 0) {  // EOF
    return Tuple2<int, int>(EOF_SENTINEL, 0);
  } else {  // return character
    return Tuple2<int, int>(buf[0], 0);
  }
}

// For read --line
// Note: this has the "FD 0 buffering issue".  See spec/ysh-place.test.sh, and
// demo/compare-strace.sh.
//
// I think that's working as intended for read --line, but we should rewrite
// pyos.Readline() to be consistent with this?  It reads one byte at a time,
// which is not what we want.

BigStr* ReadLineBuffered() {
  BigStr* result = mylib::gStdin->readline();
  // log("ReadLine() => [%s]", result->data_);
  return result;
}

Dict<BigStr*, BigStr*>* Environ() {
  auto d = Alloc<Dict<BigStr*, BigStr*>>();

  for (char** env = environ; *env; ++env) {
    char* pair = *env;

    char* eq = strchr(pair, '=');
    assert(eq != nullptr);  // must look like KEY=value

    int len = strlen(pair);

    int key_len = eq - pair;
    BigStr* key = StrFromC(pair, key_len);

    int val_len = len - key_len - 1;
    BigStr* val = StrFromC(eq + 1, val_len);

    d->set(key, val);
  }

  return d;
}

int Chdir(BigStr* dest_dir) {
  if (chdir(dest_dir->data_) == 0) {
    return 0;  // success
  } else {
    return errno;
  }
}

BigStr* GetMyHomeDir() {
  uid_t uid = getuid();  // always succeeds

  // Don't free this.  (May return a pointer to a static area)
  struct passwd* entry = getpwuid(uid);
  if (entry == nullptr) {
    return nullptr;
  }
  BigStr* s = StrFromC(entry->pw_dir);
  return s;
}

BigStr* GetHomeDir(BigStr* user_name) {
  // Don't free this.  (May return a pointer to a static area)
  struct passwd* entry = getpwnam(user_name->data_);
  if (entry == nullptr) {
    return nullptr;
  }
  BigStr* s = StrFromC(entry->pw_dir);
  return s;
}

List<PasswdEntry*>* GetAllUsers() {
  auto* ret = NewList<PasswdEntry*>();
  struct passwd* entry = nullptr;

  setpwent();
  while (true) {
    errno = 0;
    entry = getpwent();
    if (entry == nullptr) {
      if (errno == EINTR) {
        continue;  // try again
      } else if (errno != 0) {
        throw Alloc<OSError>(errno);
      }
      break;
    }
    ret->append(Alloc<PasswdEntry>(entry));
  }
  endpwent();

  return ret;
}

BigStr* GetUserName(int uid) {
  BigStr* result = kEmptyString;

  if (passwd* pw = getpwuid(uid)) {
    result = StrFromC(pw->pw_name);
  } else {
    throw Alloc<IOError>(errno);
  }

  return result;
}

BigStr* OsType() {
  BigStr* result = kEmptyString;

  utsname un = {};
  if (::uname(&un) == 0) {
    result = StrFromC(un.sysname);
  } else {
    throw Alloc<IOError>(errno);
  }

  return result;
}

Tuple3<double, double, double> Time() {
  struct timeval now;
  if (gettimeofday(&now, nullptr) < 0) {
    throw Alloc<IOError>(errno);  // could be a permission error
  }
  double real = now.tv_sec + static_cast<double>(now.tv_usec) / 1e6;

  struct rusage ru;
  if (::getrusage(RUSAGE_SELF, &ru) == -1) {
    throw Alloc<IOError>(errno);
  }
  struct timeval* u = &(ru.ru_utime);
  struct timeval* s = &(ru.ru_stime);

  double user = u->tv_sec + static_cast<double>(u->tv_usec) / 1e6;
  double sys = s->tv_sec + static_cast<double>(s->tv_usec) / 1e6;

  return Tuple3<double, double, double>(real, user, sys);
}

static void PrintClock(clock_t ticks, long ticks_per_sec) {
  double seconds = static_cast<double>(ticks) / ticks_per_sec;
  printf("%ldm%.3fs", static_cast<long>(seconds) / 60, fmod(seconds, 60));
}

// bash source: builtins/times.def
void PrintTimes() {
  struct tms t;
  if (times(&t) == -1) {
    throw Alloc<IOError>(errno);
  }
  long ticks_per_sec = sysconf(_SC_CLK_TCK);

  PrintClock(t.tms_utime, ticks_per_sec);
  putc(' ', stdout);
  PrintClock(t.tms_stime, ticks_per_sec);
  putc('\n', stdout);
  PrintClock(t.tms_cutime, ticks_per_sec);
  putc(' ', stdout);
  PrintClock(t.tms_cstime, ticks_per_sec);
  putc('\n', stdout);
}

bool InputAvailable(int fd) {
  fd_set fds;
  FD_ZERO(&fds);
  struct timeval timeout = {0};  // return immediately
  FD_SET(fd, &fds);
  return select(FD_SETSIZE, &fds, NULL, NULL, &timeout) > 0;
}

SignalSafe* InitSignalSafe() {
  gSignalSafe = Alloc<SignalSafe>();
  gHeap.RootGlobalVar(gSignalSafe);

  RegisterSignalInterest(SIGINT);  // for KeyboardInterrupt checks

  return gSignalSafe;
}

void Sigaction(int sig_num, void (*handler)(int)) {
  struct sigaction act = {};
  act.sa_handler = handler;
  if (sigaction(sig_num, &act, nullptr) != 0) {
    throw Alloc<OSError>(errno);
  }
}

static void signal_handler(int sig_num) {
  assert(gSignalSafe != nullptr);
  gSignalSafe->UpdateFromSignalHandler(sig_num);
}

void RegisterSignalInterest(int sig_num) {
  struct sigaction act = {};
  act.sa_handler = signal_handler;
  assert(sigaction(sig_num, &act, nullptr) == 0);
}

Tuple2<BigStr*, int>* MakeDirCacheKey(BigStr* path) {
  struct stat st;
  if (::stat(path->data(), &st) == -1) {
    throw Alloc<OSError>(errno);
  }

  return Alloc<Tuple2<BigStr*, int>>(path, st.st_mtime);
}

Tuple2<int, void*> PushTermAttrs(int fd, int mask) {
  struct termios* term_attrs =
      static_cast<struct termios*>(malloc(sizeof(struct termios)));

  if (tcgetattr(fd, term_attrs) < 0) {
    throw Alloc<OSError>(errno);
  }
  // Flip the bits in one field
  int orig_local_modes = term_attrs->c_lflag;
  term_attrs->c_lflag = orig_local_modes & mask;

  if (tcsetattr(fd, TCSANOW, term_attrs) < 0) {
    throw Alloc<OSError>(errno);
  }

  return Tuple2<int, void*>(orig_local_modes, term_attrs);
}

void PopTermAttrs(int fd, int orig_local_modes, void* term_attrs) {
  struct termios* t = static_cast<struct termios*>(term_attrs);
  t->c_lflag = orig_local_modes;
  if (tcsetattr(fd, TCSANOW, t) < 0) {
    ;  // Like Python, ignore error because of issue #1001
  }
}

}  // namespace pyos

namespace pyutil {

static grammar::Grammar* gOilGrammar = nullptr;

// TODO: SHARE with pyext
bool IsValidCharEscape(BigStr* c) {
  DCHECK(len(c) == 1);

  int ch = c->data_[0];

  if (ch == '/' || ch == '.' || ch == '-') {
    return false;
  }
  if (ch == ' ') {  // foo\ bar is idiomatic
    return true;
  }
  return ispunct(ch);
}

BigStr* ChArrayToString(List<int>* ch_array) {
  int n = len(ch_array);
  BigStr* result = NewStr(n);
  for (int i = 0; i < n; ++i) {
    result->data_[i] = ch_array->at(i);
  }
  result->data_[n] = '\0';
  return result;
}

BigStr* _ResourceLoader::Get(BigStr* path) {
  TextFile* t = gEmbeddedFiles;  // start of generated data
  while (t->rel_path != nullptr) {
    if (strcmp(t->rel_path, path->data_) == 0) {
      return t->contents;
    }
    t++;
  }
  // Emulate Python
  throw Alloc<IOError>(ENOENT);
}

_ResourceLoader* GetResourceLoader() {
  return Alloc<_ResourceLoader>();
}

BigStr* GetVersion(_ResourceLoader* loader) {
  return consts::gVersion;
}

void PrintVersionDetails(_ResourceLoader* loader) {
  // Invoked by core/util.py VersionFlag()
  printf("git commit = %s\n", gCommitHash);

  // TODO: I would like the CPU, OS, compiler
  // How do we get those?  Look at CPython
}

BigStr* BackslashEscape(BigStr* s, BigStr* meta_chars) {
  int upper_bound = len(s) * 2;
  BigStr* buf = OverAllocatedStr(upper_bound);
  char* p = buf->data_;

  for (int i = 0; i < len(s); ++i) {
    char c = s->data_[i];
    if (memchr(meta_chars->data_, c, len(meta_chars))) {
      *p++ = '\\';
    }
    *p++ = c;
  }
  buf->MaybeShrink(p - buf->data_);
  return buf;
}

BigStr* strerror(IOError_OSError* e) {
  BigStr* s = StrFromC(::strerror(e->errno_));
  return s;
}

grammar::Grammar* LoadYshGrammar(_ResourceLoader*) {
  if (gOilGrammar != nullptr) {
    return gOilGrammar;
  }

  gOilGrammar = Alloc<grammar::Grammar>();
  gHeap.RootGlobalVar(gOilGrammar);
  return gOilGrammar;
}

}  // namespace pyutil
