// core_pyerror.h

#ifndef CORE_PYERROR_H
#define CORE_PYERROR_H

// STUBS for p_die()
// [[noreturn]] avoids warnings
[[noreturn]] void p_die(Str* s, int span_id) {
  throw new error::Parse(s, span_id);
}

[[noreturn]] void p_die(Str* s, syntax_asdl::Token* token) {
  throw new error::Parse(s, token);
}

[[noreturn]] void p_die(Str* s, syntax_asdl::word_part_t* part) {
  throw new error::Parse(s, part);
}

[[noreturn]] void p_die(Str* s, syntax_asdl::word_t* w) {
  throw new error::Parse(s, w);
}

[[noreturn]] void e_die(Str* s) {
  throw new error::FatalRuntime(s);
}

[[noreturn]] void e_die(Str* s, int span_id) {
  throw new error::FatalRuntime(s);
}

[[noreturn]] void e_die(Str* s, syntax_asdl::Token* token) {
  throw new error::FatalRuntime(s);
}

[[noreturn]] void e_die(Str* s, syntax_asdl::word_part_t* part) {
  throw new error::FatalRuntime(s);
}

[[noreturn]] void e_die(Str* s, syntax_asdl::word_t* w) {
  throw new error::FatalRuntime(s);
}

[[noreturn]] void e_strict(Str* s, int span_id) {
  throw new error::Strict(s);
}

[[noreturn]] void e_strict(Str* s, syntax_asdl::Token* token) {
  throw new error::Strict(s);
}

[[noreturn]] void e_strict(Str* s, syntax_asdl::word_part_t* part) {
  throw new error::Strict(s);
}

[[noreturn]] void e_strict(Str* s, syntax_asdl::word_t* w) {
  throw new error::Strict(s);
}

// Used without args in osh/string_ops.py
[[noreturn]] void e_strict(Str* s) {
  throw new error::Strict(s);
}

// e.g. used in core/state.py
[[noreturn]] void e_usage(Str* s) {
  throw new error::Usage(s, -1);  // NO_SPID
}

[[noreturn]] void e_usage(Str* s, int span_id) {
  throw new error::Usage(s, span_id);
}

#endif  // CORE_PYERROR_H
