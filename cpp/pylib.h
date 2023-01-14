// pylib.h: Replacement for pylib/*.py

#ifndef LEAKY_PYLIB_H
#define LEAKY_PYLIB_H

#include "mycpp/runtime.h"

namespace os_path {

Str* rstrip_slashes(Str* s);

}  // namespace os_path

namespace path_stat {

bool exists(Str* path);

bool isdir(Str* path);

}  // namespace path_stat

#endif  // LEAKY_PYLIB_H
