// core_pyutil.cc

#include "core_pyutil.h"

namespace pyutil {

bool IsValidCharEscape(int c) {
  if (c == '/' || c == '.' || c == '-') {
    return false;
  }
  if (c == ' ') {  // foo\ bar is idiomatic
    return true;
  }
  return ispunct(c);
}

Str* ChArrayToString(List<int>* ch_array) {
  int n = len(ch_array);
  unsigned char* buf = static_cast<unsigned char*>(malloc(n + 1));
  for (int i = 0; i < n; ++i) {
    buf[i] = ch_array->index_(i);
  }
  buf[n] = '\0';
  return new Str(reinterpret_cast<char*>(buf), n);
}

Str* _ResourceLoader::Get(Str* path) {
  return new Str("TODO");
}

_ResourceLoader* GetResourceLoader() {
  return new _ResourceLoader();
}

void CopyFile(Str* in_path, Str* out_path) {
  assert(0);
}

Str* GetVersion(_ResourceLoader* loader) {
  return new Str("TODO");
}

Str* ShowAppVersion(Str* app_name, _ResourceLoader* loader) {
  assert(0);
}

// Avoid conflict with field
#undef errno

Str* strerror(_OSError* e) {
  return new Str(::strerror(e->errno));
}

}  // namespace pyutil
