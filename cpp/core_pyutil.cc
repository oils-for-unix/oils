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

}  // namespace pyutil
