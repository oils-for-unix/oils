// pylib_os_path.h

#ifndef PYLIB_OS_PATH_H
#define PYLIB_OS_PATH_H

namespace os_path {

Str kSlash = {"/", 1};

// This function takes varargs.  Add other varargs variants?
inline Str* join(Str* s1, Str* s2) {
  if (s2->startswith(&kSlash)) {
    // absolute path, like Python's behavior.  I think we use this in 'cd'
    return s2;
  }
  if (s1->endswith(&kSlash)) {
    return str_concat(s1, s2);
  }
  return str_concat3(s1, &kSlash, s2);
}

// Note: This is a complicated algorithm in Python.  Do we have to match it, or
// is there a libc equivalent?
inline Str* normpath(Str* path) {
  assert(0);
}

inline Str* abspath(Str* path) {
  if (!path->startswith(&kSlash)) {
    auto cwd = posix::getcwd();
    path = join(cwd, path);
  }
  return normpath(path);
}

inline Str* basename(Str* path) {
  assert(0);
}

}  // namespace os_path

#endif  // PYLIB_OS_PATH_H
