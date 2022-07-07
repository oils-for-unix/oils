// pylib_os_path_leaky.h

#ifndef PYLIB_OS_PATH_H
#define PYLIB_OS_PATH_H

#if 1  // TODO: switch this off
#include "mycpp/mylib_leaky.h"
#else
#include "mycpp/mylib2.h"
#endif

namespace os_path {

Str* rstrip_slashes(Str* s);

}  // namespace os_path

#endif  // PYLIB_OS_PATH_H
