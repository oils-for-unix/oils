// pylib_path_stat.h

#ifndef PYLIB_PATH_STAT_H
#define PYLIB_PATH_STAT_H

namespace path_stat {

inline bool exists(Str* path) {
  mylib::Str0 path0(path);
  struct stat st;
  if (::stat(path0.Get(), &st) < 0) {
    return false;
  } else {
    return true;
  }
}

}  // namespace path_stat

#endif  // PYLIB_PATH_STAT_H
