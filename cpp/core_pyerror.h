// core_pyerror.h

#ifndef CORE_PYERROR_H
#define CORE_PYERROR_H

#include "_gen/frontend/syntax.asdl.h"

// STUBS for varargs functions like p_die()
// [[noreturn]] avoids warnings.  TODO: Could just use 'raise' in Python

namespace loc = syntax_asdl::loc;

[[noreturn]] inline void e_die(Str* s) {
  throw Alloc<error::FatalRuntime>(1, s, Alloc<loc::Missing>());
}

[[noreturn]] inline void e_die(Str* s, syntax_asdl::loc_t* location) {
  throw Alloc<error::FatalRuntime>(1, s, location);
}

#endif  // CORE_PYERROR_H
