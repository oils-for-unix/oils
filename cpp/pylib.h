// pylib.h: Replacement for pylib/*.py

#ifndef LEAKY_PYLIB_H
#define LEAKY_PYLIB_H

#include "mycpp/runtime.h"

namespace os_path {

BigStr* rstrip_slashes(BigStr* s);

}  // namespace os_path

namespace path_stat {

bool exists(BigStr* path);

bool isdir(BigStr* path);

}  // namespace path_stat

#endif  // LEAKY_PYLIB_H
