// core_pyerror.h

#ifndef CORE_PYERROR_H
#define CORE_PYERROR_H

#include "_gen/frontend/syntax.asdl.h"

// STUBS for varargs functions like p_die()
// [[noreturn]] avoids warnings

[[noreturn]] inline void p_die(Str* s, int span_id) {
  throw Alloc<error::Parse>(s, span_id);
}

[[noreturn]] inline void p_die(Str* s, syntax_asdl::Token* token) {
  throw Alloc<error::Parse>(s, token);
}

[[noreturn]] inline void p_die(Str* s, syntax_asdl::word_part_t* part) {
  throw Alloc<error::Parse>(s, part);
}

[[noreturn]] inline void p_die(Str* s, syntax_asdl::word_t* w) {
  throw Alloc<error::Parse>(s, w);
}

// TODO: pass location info everywhere

[[noreturn]] inline void e_die(Str* s) {
  throw Alloc<error::FatalRuntime>(s);
}

[[noreturn]] inline void e_die(Str* s, syntax_asdl::loc_t* location) {
  throw Alloc<error::FatalRuntime>(s);
}

[[noreturn]] inline void e_die_status(int status, Str* s) {
  throw Alloc<error::FatalRuntime>(status, s);
}

[[noreturn]] inline void e_die_status(int status, Str* s,
                                      syntax_asdl::loc_t* location) {
  throw Alloc<error::FatalRuntime>(status, s);
}

[[noreturn]] inline void e_strict(Str* s, syntax_asdl::loc_t* location) {
  throw Alloc<error::Strict>(s);
}

// e.g. used in core/state.py
[[noreturn]] inline void e_usage(Str* s) {
  throw Alloc<error::Usage>(s, -1);  // NO_SPID
}

[[noreturn]] inline void e_usage(Str* s, int span_id) {
  throw Alloc<error::Usage>(s, span_id);
}

#endif  // CORE_PYERROR_H
