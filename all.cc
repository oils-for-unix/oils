// NOTE(Jesse): Hack so we don't redefine a bunch of stuff that myccp generates
// multiple times
#define RUNTIME_H

#include "mycpp/leaky_mylib.cc"
#include "cpp/leaky_stdlib.cc"
#include "cpp/leaky_core.cc" // undef's errno


/* #include "cpp/leaky_preamble.h" */


#include "_gen/frontend/id_kind.asdl.cc"
#include "mycpp/marksweep_heap.cc"
#include "mycpp/leaky_builtins.cc"
#include "cpp/leaky_pylib.cc"
#include "mycpp/cheney_heap.cc"
#include "mycpp/leaky_containers.cc"
#include "mycpp/gc_mylib.cc"
#include "cpp/leaky_libc.cc"
#include "_gen/frontend/arg_types.cc"
#include "_gen/frontend/consts.cc"
#include "cpp/leaky_pgen2.cc"
#include "cpp/leaky_frontend_tdop.cc"
#include "_gen/osh/arith_parse.cc"
#include "cpp/leaky_osh.cc"
#include "cpp/leaky_frontend_match.cc"

const char* command_str(int tag);
/* hnode_t* syntax_asdl::parse_result_t::_AbbreviatedTree() { return {}; } */

#include "_gen/bin/osh_eval.mycpp.cc" // defines a bunch of pretty-printing code that we #if 0'd out with the #define RUNTIME_H above

#include "_gen/frontend/syntax.asdl.cc"
#include "cpp/leaky_frontend_flag_spec.cc"
#include "_gen/core/runtime.asdl.cc"

