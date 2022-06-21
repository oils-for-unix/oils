// osh_bool_stat.h

#ifndef OSH_BOOL_STAT_H
#define OSH_BOOL_STAT_H

#include <sys/stat.h>

#include "mylib.h"
#include "syntax_asdl.h"

namespace bool_stat {

namespace Id = id_kind_asdl::Id;
using syntax_asdl::word_t;

bool isatty(Str* fd_str, word_t* blame_word);

inline bool DoUnaryOp(Id_t op_id, Str* s) {
  mylib::Str0 path(s);

  // TODO: also call lstat(), etc.

  const char *zPath = path.Get();

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

  // NOTE(Jesse): The python OSH interpreter implements -r, -w, -x (in bool_stat.py)
  // using posix.access(), which is effectively a thunk to C access().
  //
  // https://github.com/python/cpython/blob/8d999cbf4adea053be6dbb612b9844635c4dfb8e/Modules/posixmodule.c#L2547
  //
  // We cannot use the `stat` struct because the python analogue for these
  // checks permission for the _calling_process_, which would end up being
  // pretty obtuse if we used the information contained in the `stat` struct.
  // It contains rwx information for owner, group, and other; we'd have
  // to figure out which of those our process belonged to.
    case Id::BoolUnary_x:
      return access(zPath, X_OK) == 0;
  //
    case Id::BoolUnary_r:
      return access(zPath, R_OK) == 0;
  //
    case Id::BoolUnary_w:
      return access(zPath, W_OK) == 0;
  // end note
  }


  assert(0);
}

inline bool DoBinaryOp(Id_t op_id, Str* s1, Str* s2) {
  mylib::Str0 left0(s1);
  mylib::Str0 right0(s2);

  int m1 = 0;
  struct stat st1;
  if (stat(left0.Get(), &st1) == 0) {
    m1 = st1.st_mtime;
  }

  int m2 = 0;
  struct stat st2;
  if (stat(right0.Get(), &st2) == 0) {
    m2 = st2.st_mtime;
  }

  switch (op_id) {
  case Id::BoolBinary_nt:
    return m1 > m2;
  case Id::BoolBinary_ot:
    return m1 < m2;
  }

  assert(0);
}

}  // namespace bool_stat

#endif  // OSH_BOOL_STAT_H
