// pylib_os_path.h

#ifndef PYLIB_OS_PATH_H
#define PYLIB_OS_PATH_H

#if 1  // TODO: switch this off
#include "mylib.h"
#else
#include "mylib2.h"
#endif

namespace os_path {

Str* rstrip_slashes(Str* s);
 
}  // namespace os_path

#endif  // PYLIB_OS_PATH_H

