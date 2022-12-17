// core.cc

#include "cpp/core.h"

#include <errno.h>
#include <pwd.h>  // passwd
#include <signal.h>
#include <sys/resource.h>  // getrusage
#include <sys/times.h>     // tms / times()
#include <sys/utsname.h>   // uname
#include <sys/wait.h>      // waitpid()
#include <time.h>          // time()
#include <unistd.h>        // getuid(), environ

namespace pyos {

static SignalHandler* gSignalHandler = nullptr;

Tuple2<int, int> WaitPid() {
  int status;
  int result = ::waitpid(-1, &status, WUNTRACED);
  if (result < 0) {
    return Tuple2<int, int>(-1, errno);
  }
  return Tuple2<int, int>(result, status);
}

Tuple2<int, int> Read(int fd, int n, List<Str*>* chunks) {
  Str* s = OverAllocatedStr(n);  // Allocate enough for the result

  int length = ::read(fd, s->data(), n);
  if (length < 0) {
    return Tuple2<int, int>(-1, errno);
  }
  if (length == 0) {
    return Tuple2<int, int>(length, 0);
  }

  // Now we know how much data we got back
  s->SetObjLenFromStrLen(length);
  chunks->append(s);

  return Tuple2<int, int>(length, 0);
}

Tuple2<int, int> ReadByte(int fd) {
  unsigned char buf[1];
  ssize_t n = read(fd, &buf, 1);
  if (n < 0) {  // read error
    return Tuple2<int, int>(-1, errno);
  } else if (n == 0) {  // EOF
    return Tuple2<int, int>(EOF_SENTINEL, 0);
  } else {  // return character
    return Tuple2<int, int>(buf[0], 0);
  }
}

// for read --line
Str* ReadLine() {
  assert(0);  // Does this get called?
}

Dict<Str*, Str*>* Environ() {
  auto d = NewDict<Str*, Str*>();

  for (char** env = environ; *env; ++env) {
    char* pair = *env;

    char* eq = strchr(pair, '=');
    assert(eq != nullptr);  // must look like KEY=value

    int len = strlen(pair);

    int key_len = eq - pair;
    Str* key = StrFromC(pair, key_len);

    int val_len = len - key_len - 1;
    Str* val = StrFromC(eq + 1, val_len);

    d->set(key, val);
  }

  return d;
}

int Chdir(Str* dest_dir) {
  if (chdir(dest_dir->data_) == 0) {
    return 0;  // success
  } else {
    return errno;
  }
}

Str* GetMyHomeDir() {
  uid_t uid = getuid();  // always succeeds

  // Don't free this.  (May return a pointer to a static area)
  struct passwd* entry = getpwuid(uid);
  if (entry == nullptr) {
    return nullptr;
  }
  Str* s = StrFromC(entry->pw_dir);
  return s;
}

Str* GetHomeDir(Str* user_name) {
  // Don't free this.  (May return a pointer to a static area)
  struct passwd* entry = getpwnam(user_name->data_);
  if (entry == nullptr) {
    return nullptr;
  }
  Str* s = StrFromC(entry->pw_dir);
  return s;
}

Str* GetUserName(int uid) {
  Str* result = kEmptyString;

  if (passwd* pw = getpwuid(uid)) {
    result = StrFromC(pw->pw_name);
  } else {
    throw Alloc<IOError>(errno);
  }

  return result;
}

Str* OsType() {
  Str* result = kEmptyString;

  utsname un = {};
  if (::uname(&un) == 0) {
    result = StrFromC(un.sysname);
  } else {
    throw Alloc<IOError>(errno);
  }

  return result;
}

Tuple3<double, double, double> Time() {
  rusage ru;  // NOTE(Jesse): Doesn't have to be cleared to 0.  The kernel
              // clears unused fields.
  if (::getrusage(RUSAGE_SELF, &ru) == -1) {
    throw Alloc<IOError>(errno);
  }

  time_t t = ::time(nullptr);
  auto result = Tuple3<double, double, double>(
      static_cast<double>(t), static_cast<double>(ru.ru_utime.tv_sec),
      static_cast<double>(ru.ru_stime.tv_sec));
  return result;
}

void PrintTimes() {
  tms t;
  if (times(&t) == -1) {
    throw Alloc<IOError>(errno);
  } else {
    {
      int user_minutes = t.tms_utime / 60;
      float user_seconds = t.tms_utime % 60;
      int system_minutes = t.tms_stime / 60;
      float system_seconds = t.tms_stime % 60;
      printf("%dm%1.3fs %dm%1.3fs\n", user_minutes, user_seconds,
             system_minutes, system_seconds);
    }

    {
      int child_user_minutes = t.tms_cutime / 60;
      float child_user_seconds = t.tms_cutime % 60;
      int child_system_minutes = t.tms_cstime / 60;
      float child_system_seconds = t.tms_cstime % 60;
      printf("%dm%1.3fs %dm%1.3fs", child_user_minutes, child_user_seconds,
             child_system_minutes, child_system_seconds);
    }
  }
}

bool InputAvailable(int fd) {
  NotImplemented();
}

void SignalHandler::Update(int sig_num) {
  assert(signal_queue_ != nullptr);
  assert(signal_queue_->len_ < signal_queue_->capacity_);
  signal_queue_->append(sig_num);
  if (sig_num == SIGWINCH) {
    sig_num = sigwinch_num_;
  }
  last_sig_num_ = sig_num;
}

static List<int>* AllocSignalQueue() {
  List<int>* ret = NewList<int>();
  ret->reserve(kMaxSignalsInFlight);
  return ret;
}

List<int>* SignalHandler::TakeSignalQueue() {
  List<int>* new_queue = AllocSignalQueue();
  List<int>* ret = signal_queue_;
  signal_queue_ = new_queue;
  return ret;
}

void Sigaction(int sig_num, sighandler_t handler) {
  struct sigaction act = {};
  act.sa_handler = handler;
  if (sigaction(sig_num, &act, nullptr) != 0) {
    throw Alloc<OSError>(errno);
  }
}

static void signal_handler(int sig_num) {
  assert(gSignalHandler != nullptr);
  gSignalHandler->Update(sig_num);
}

void RegisterSignalInterest(int sig_num) {
  struct sigaction act = {};
  act.sa_handler = signal_handler;
  assert(sigaction(sig_num, &act, nullptr) == 0);
}

List<int>* TakeSignalQueue() {
  assert(gSignalHandler != nullptr);
  return gSignalHandler->TakeSignalQueue();
}

int LastSignal() {
  assert(gSignalHandler != nullptr);
  return gSignalHandler->last_sig_num_;
}

void SetSigwinchCode(int code) {
  assert(gSignalHandler != nullptr);
  gSignalHandler->sigwinch_num_ = code;
}

void InitShell() {
  gSignalHandler = Alloc<SignalHandler>();
  gHeap.RootGlobalVar(gSignalHandler);
  gSignalHandler->signal_queue_ = AllocSignalQueue();
}

}  // namespace pyos

namespace pyutil {

bool IsValidCharEscape(int c) {
  if (c == '/' || c == '.' || c == '-') {
    return false;
  }
  if (c == ' ') {  // foo\ bar is idiomatic
    return true;
  }
  return ispunct(c);
}

Str* ChArrayToString(List<int>* ch_array) {
  int n = len(ch_array);
  Str* result = NewStr(n);
  for (int i = 0; i < n; ++i) {
    result->data_[i] = ch_array->index_(i);
  }
  result->data_[n] = '\0';
  return result;
}

Str* _ResourceLoader::Get(Str* path) {
  /* NotImplemented(); */
  return StrFromC("TODO");
}

_ResourceLoader* GetResourceLoader() {
  return Alloc<_ResourceLoader>();
}

void CopyFile(Str* in_path, Str* out_path) {
  assert(0);
}

Str* GetVersion(_ResourceLoader* loader) {
  /* NotImplemented(); */
  return StrFromC("TODO");
}

Str* ShowAppVersion(Str* app_name, _ResourceLoader* loader) {
  assert(0);
}

Str* BackslashEscape(Str* s, Str* meta_chars) {
  int upper_bound = len(s) * 2;
  Str* buf = OverAllocatedStr(upper_bound);
  char* p = buf->data_;

  for (int i = 0; i < len(s); ++i) {
    char c = s->data_[i];
    if (memchr(meta_chars->data_, c, len(meta_chars))) {
      *p++ = '\\';
    }
    *p++ = c;
  }
  buf->SetObjLenFromStrLen(p - buf->data_);
  return buf;
}

Str* strerror(IOError_OSError* e) {
  Str* s = StrFromC(::strerror(e->errno_));
  return s;
}

}  // namespace pyutil
