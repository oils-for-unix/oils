// core_pyutil.h

#ifndef CORE_PYUTIL_H
#define CORE_PYUTIL_H

#include "mylib.h"

namespace pyutil {

class _ResourceLoader {
};

_ResourceLoader* GetResourceLoader();

void CopyFile(Str* in_path, Str* out_path);

Str* GetVersion(_ResourceLoader* loader);

Str* ShowAppVersion(Str* app_name, _ResourceLoader* loader);
 
}  // namespace pyutil

#endif  // CORE_PYUTIL_H

