#include "id_kind_asdl.h"  // syntax.asdl depends on this

using id_kind_asdl::Id_t;  // TODO: proper ASDL modules may eliminate this
using id_kind_asdl::Kind_t;

#include "runtime_asdl.h"
#include "syntax_asdl.h"
#include "types_asdl.h"

// oil/_devbuild/gen-cpp
#include "lookup.h"
#include "grammar_nt.h"

// oil/cpp
#include "asdl_pretty.h"
#include "core_error.h"
#include "frontend_match.h"
#include "frontend_tdop.h"
#include "osh_arith_parse.h"

// Hack for now.  Every sum type should have repr()?
Str* repr(syntax_asdl::source_t* obj) {
  return new Str("TODO");
}

// STUB for osh/word_.py
Str* str(syntax_asdl::word_t* w) {
  return new Str("TODO");
}

// For hnode::External in asdl/format.py
Str* repr(void* obj) {
  return new Str("TODO: repr()");
}

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

[[noreturn]] void e_die(Str* s, int span_id) {
  assert(0);
}

[[noreturn]] void e_die(Str* s, syntax_asdl::Token* token) {
  assert(0);
}

[[noreturn]] void e_die(Str* s, syntax_asdl::word_part_t* part) {
  assert(0);
}

[[noreturn]] void e_die(Str* s, syntax_asdl::word_t* w) {
  assert(0);
}
