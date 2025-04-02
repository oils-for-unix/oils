// core.h: Replacement for core/*.py

#ifndef CORE_H
#define CORE_H

#include <pwd.h>  // passwd
#include <termios.h>

#include "_gen/frontend/syntax.asdl.h"
#include "cpp/pgen2.h"
#include "mycpp/runtime.h"

// Hacky forward declaration
namespace completion {
class RootCompleter;
};

namespace pyos {

const int TERM_ICANON = ICANON;
const int TERM_ECHO = ECHO;
const int EOF_SENTINEL = 256;
const int NEWLINE_CH = 10;

Tuple2<int, int> WaitPid(int waitpid_options);
Tuple2<int, int> Read(int fd, int n, List<BigStr*>* chunks);
Tuple2<int, int> ReadByte(int fd);
BigStr* ReadLineBuffered();
Dict<BigStr*, BigStr*>* Environ();
int Chdir(BigStr* dest_dir);
BigStr* GetMyHomeDir();
BigStr* GetHomeDir(BigStr* user_name);

class ReadError {
 public:
  explicit ReadError(int err_num_) : err_num(err_num_) {
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(kZeroMask, sizeof(ReadError));
  }

  int err_num;
};

class PasswdEntry {
 public:
  explicit PasswdEntry(const passwd* entry)
      : pw_name(StrFromC(entry->pw_name)),
        pw_uid(entry->pw_uid),
        pw_gid(entry->pw_gid) {
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(PasswdEntry));
  }

  BigStr* pw_name;
  int pw_uid;
  int pw_gid;

  static constexpr uint32_t field_mask() {
    return maskbit(offsetof(PasswdEntry, pw_name));
  }
};

List<PasswdEntry*>* GetAllUsers();

BigStr* GetUserName(int uid);

BigStr* OsType();

Tuple2<mops::BigInt, mops::BigInt> GetRLimit(int resource);

void SetRLimit(int resource, mops::BigInt soft, mops::BigInt hard);

Tuple3<double, double, double> Time();

void PrintTimes();

bool InputAvailable(int fd);

List<int>* WaitForReading(List<int>* fds_in);

IOError_OSError* FlushStdout();

Tuple2<int, void*> PushTermAttrs(int fd, int mask);
void PopTermAttrs(int fd, int orig_local_modes, void* term_attrs);

Tuple2<BigStr*, int>* MakeDirCacheKey(BigStr* path);

}  // namespace pyos

namespace pyutil {

double infinity();
double nan();

bool IsValidCharEscape(BigStr* c);
BigStr* ChArrayToString(List<int>* ch_array);

class _ResourceLoader {
 public:
  _ResourceLoader() {
  }

  virtual BigStr* Get(BigStr* path);

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(kZeroMask, sizeof(_ResourceLoader));
  }
};

_ResourceLoader* GetResourceLoader();

BigStr* GetVersion(_ResourceLoader* loader);

void PrintVersionDetails(_ResourceLoader* loader);

BigStr* strerror(IOError_OSError* e);

BigStr* BackslashEscape(BigStr* s, BigStr* meta_chars);

grammar::Grammar* LoadYshGrammar(_ResourceLoader*);

}  // namespace pyutil

#endif  // CORE_H
