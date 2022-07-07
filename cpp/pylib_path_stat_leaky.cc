// pylib_path_stat.cc

#include "pylib_path_stat_leaky.h"

#include <sys/stat.h>

#include "mycpp/mylib_leaky.h"

namespace path_stat {

bool exists(Str* path) {
  mylib::Str0 path0(path);
  struct stat st;
  if (::stat(path0.Get(), &st) < 0) {
    return false;
  } else {
    return true;
  }
}

}  // namespace path_stat
