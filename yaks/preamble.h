// yaks/preamble.h: declarations to run translated yaks_main.py

#include <errno.h>

#include "_gen/core/value.asdl.h"  // could break this dep from j8?
#include "_gen/data_lang/nil8.asdl.h"
#include "_gen/display/pretty.asdl.h"
#include "_gen/frontend/consts.h"
#include "_gen/frontend/id_kind.asdl.h"  // syntax.asdl depends on this
#include "_gen/frontend/syntax.asdl.h"
#include "_gen/yaks/yaks.asdl.h"
#include "cpp/data_lang.h"
#include "cpp/frontend_match.h"
#include "cpp/stdlib.h"     // needed for math::{isnan,isinf}
#include "mycpp/runtime.h"  // runtime library e.g. with Python data structures

// TODO: Why do we need these?
using pretty_asdl::doc;
using value_asdl::value;
using yaks_asdl::mod_def;
using syntax_asdl::command;
using syntax_asdl::expr;
