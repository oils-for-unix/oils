// errno_.h

#ifndef ERRNO__H
#define ERRNO__H

// For _build/cpp/osh_eval.cc, etc.  The bindings in cpp/posix.cc, etc. will
// use <errno.h>, but they don't include "errno_.h"
#undef errno

// We're using the errno_:: versions
#undef EBADF
#undef ENOEXEC
#undef EACCES
#undef ENOENT
#undef ECHILD

namespace errno_ {

extern int EBADF;
extern int ENOEXEC;
extern int EACCES;
extern int ENOENT;
extern int ECHILD;

}  // namespace errno_

#endif  // ERRNO__H
