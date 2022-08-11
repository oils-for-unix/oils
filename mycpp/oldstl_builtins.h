#ifndef OLDSTL_BINDINGS
  #error "This file contains definitions for OLDSTL builtins."
#endif

#include "mycpp/gc_builtins.h"

// mycpp doesn't understand dynamic format strings yet
inline Str* dynamic_fmt_dummy() {
  /* NotImplemented(); */
  return StrFromC("dynamic_fmt_dummy");
}
