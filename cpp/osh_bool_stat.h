// osh_bool_stat.h

#ifndef OSH_BOOL_STAT_H
#define OSH_BOOL_STAT_H

#include <sys/stat.h>

#include "mylib.h"
#include "syntax_asdl.h"

namespace bool_stat {

namespace Id = id_kind_asdl::Id;
using syntax_asdl::word_t;

inline bool isatty(int fd, Str* s, word_t* blame_word) {
  assert(0);
}

inline bool DoUnaryOp(Id_t op_id, Str* s) {
  mylib::Str0 path(s);

  // TODO: also call lstat(), etc.
  struct stat st;
  if (stat(path.Get(), &st) < 0) {
    return false;
  }

  switch (op_id) {
  // synonyms for existence
  case Id::BoolUnary_a:
  case Id::BoolUnary_e:
    return true;
  }
  assert(0);
}

inline bool DoBinaryOp(Id_t op_id, Str* s1, Str* s2) {
  assert(0);
}

}  // namespace bool_stat

#endif  // OSH_BOOL_STAT_H
