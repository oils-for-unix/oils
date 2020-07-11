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
  struct stat st;
  if (stat(path.Get(), &st) < 0) {
    return false;
  }
  auto mode = st.st_mode;

  switch (op_id) {
  // synonyms for existence
  case Id::BoolUnary_a:
  case Id::BoolUnary_e:
    return true;

  case Id::BoolUnary_k:
    return (mode & S_ISVTX) != 0;
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
