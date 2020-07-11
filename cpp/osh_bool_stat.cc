// osh_bool_stat.cc

#include <unistd.h>

#include "core_error.h"
#include "core_pyerror.h"
#include "osh_bool_stat.h"

namespace bool_stat {

bool isatty(Str* fd_str, word_t* blame_word) {
  int fd;
  try {
    fd = to_int(fd_str);
  } catch (ValueError* e) {
    // Note we don't have printf formatting here
    e_die(new Str("Invalid file descriptor TODO"), blame_word);
  }
  // note: we don't check errno
  int result = ::isatty(fd);
  return result;
}

}  // namespace bool_stat
