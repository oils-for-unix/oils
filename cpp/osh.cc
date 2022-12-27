// osh.cc

#include "cpp/osh.h"

#include <fcntl.h>  // AT_* Constants
#include <sys/stat.h>
#include <unistd.h>

#include "cpp/core_error.h"
#include "cpp/core_pyerror.h"
#include "mycpp/gc_builtins.h"

namespace arith_parse {

tdop::ParserSpec kArithSpec;

}  // namespace arith_parse

namespace Id = id_kind_asdl::Id;  // used below

namespace bool_stat {

bool isatty(Str* fd_str, word_t* blame_word) {
  int fd;
  try {
    fd = to_int(fd_str);
  } catch (ValueError* e) {
    // Note we don't have printf formatting here
    e_die(StrFromC("Invalid file descriptor TODO"), blame_word);
  }
  // note: we don't check errno
  int result = ::isatty(fd);
  return result;
}

bool DoUnaryOp(Id_t op_id, Str* s) {
  const char* zPath = s->data_;

  if (op_id == Id::BoolUnary_h || op_id == Id::BoolUnary_L) {
    struct stat st;
    if (lstat(zPath, &st) < 0) {
      return false;
    }

    return S_ISLNK(st.st_mode);
  } else {
    struct stat st;
    if (stat(zPath, &st) < 0) {
      return false;
    }

    auto mode = st.st_mode;

    switch (op_id) {
    // synonyms for existence
    case Id::BoolUnary_a:
    case Id::BoolUnary_e:
      return true;

    case Id::BoolUnary_s:
      return st.st_size != 0;

    case Id::BoolUnary_d:
      return S_ISDIR(mode);

    case Id::BoolUnary_f:
      return S_ISREG(mode);

    case Id::BoolUnary_k:
      return (mode & S_ISVTX) != 0;

    case Id::BoolUnary_p:
      return S_ISFIFO(mode);

    case Id::BoolUnary_O:
      return st.st_uid == geteuid();

    case Id::BoolUnary_G:
      return st.st_gid == getegid();

    case Id::BoolUnary_u:
      return mode & S_ISUID;

    case Id::BoolUnary_g:
      return mode & S_ISGID;

      // NOTE(Jesse): This implementation MAY have a bug.  On my system (Ubuntu
      // 20.04) it returns a correct result if the user is root (elevated with
      // sudo) and no execute bits are set for a file.
      //
      // A bug worked around in the python `posix` module here is that the above
      // (working) scenario is not always the case.
      //
      // https://github.com/python/cpython/blob/8d999cbf4adea053be6dbb612b9844635c4dfb8e/Modules/posixmodule.c#L2547
      //
      // As well as the dash source code found here (relative to this repo
      // root):
      //
      // _cache/spec-bin/dash-0.5.10.2/src/bltin/test.c
      // See `test_file_access()`
      //
      // We could also use the `stat` struct to manually compute the
      // permissions, as shown in the above `test.c`, though the code is
      // somewhat obtuse.
      //
      // There is further discussion of this issue in:
      // https://github.com/oilshell/oil/pull/1168
      //
      // And a bug filed for it at:
      //
      // https://github.com/oilshell/oil/issues/1170
      //
    case Id::BoolUnary_x:
      return faccessat(AT_FDCWD, zPath, X_OK, AT_EACCESS) == 0;
      //

    case Id::BoolUnary_r:
      return faccessat(AT_FDCWD, zPath, R_OK, AT_EACCESS) == 0;

    case Id::BoolUnary_w:
      return faccessat(AT_FDCWD, zPath, W_OK, AT_EACCESS) == 0;
    }
  }

  FAIL(kShouldNotGetHere);
}

bool DoBinaryOp(Id_t op_id, Str* s1, Str* s2) {
  int m1 = 0;
  struct stat st1;
  if (stat(s1->data_, &st1) == 0) {
    m1 = st1.st_mtime;
  }

  int m2 = 0;
  struct stat st2;
  if (stat(s2->data_, &st2) == 0) {
    m2 = st2.st_mtime;
  }

  switch (op_id) {
  case Id::BoolBinary_nt:
    return m1 > m2;
  case Id::BoolBinary_ot:
    return m1 < m2;
  case Id::BoolBinary_ef:
    return st1.st_dev == st2.st_dev && st1.st_ino == st2.st_ino;
  }

  FAIL(kShouldNotGetHere);
}

}  // namespace bool_stat
