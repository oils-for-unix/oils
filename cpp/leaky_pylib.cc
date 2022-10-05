// leaky_pylib.cc

#include "leaky_pylib.h"

#include <sys/stat.h>

namespace os_path {

Str* rstrip_slashes(Str* s) {
  // Strip all the rightmost slashes, but not if it's ALL slashes
  int n = len(s);
  if (n == 0) {
    return s;
  }

  int new_len = n;
  for (int i = n - 1; i >= 0; i--) {
    char c = s->data_[i];
    if (c == '/') {
      new_len--;
    } else {
      break;
    }
  }

  if (new_len == 0) {  // it was all slashes, don't strip
    return s;
  }

  // Truncate to new_len
  Str* result = AllocStr(new_len);
  memcpy(result->data_, s->data_, new_len);
  result->data_[new_len] = '\0';
  return result;
}

}  // namespace os_path

namespace path_stat {

bool exists(Str* path) {
  struct stat st;
  if (::stat(path->data_, &st) < 0) {
    return false;
  } else {
    return true;
  }
}

}  // namespace path_stat
