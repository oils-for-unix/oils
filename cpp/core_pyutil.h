// core_pyutil.h

#ifndef CORE_PYUTIL_H
#define CORE_PYUTIL_H

#include "mylib.h"

namespace pyutil {

class _ResourceLoader {
 public:
  virtual Str* Get(Str* path);
};

_ResourceLoader* GetResourceLoader();

void CopyFile(Str* in_path, Str* out_path);

Str* GetVersion(_ResourceLoader* loader);

Str* ShowAppVersion(Str* app_name, _ResourceLoader* loader);

inline Str* strerror_IO(IOError* e) {
  assert(0);
}

inline Str* strerror_OS(OSError* e) {
  assert(0);
}

}  // namespace pyutil

#endif  // CORE_PYUTIL_H
