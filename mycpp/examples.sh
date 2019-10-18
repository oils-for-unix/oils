# examples.sh: Hooks for specific files


#
# examples/parse
#

typecheck-parse() {
  local name='parse'
  local flags='--no-strict-optional'

  set +o errexit
  MYPYPATH="$REPO_ROOT" \
    mypy --py2 --strict $flags examples/parse.py | tee _tmp/err.txt
  set -o errexit

  # Stupid fastlex error in asdl/pretty.py

  local num_errors=$(grep -v 'Found 1 error in 1 file' _tmp/err.txt | wc -l)
  if [[ $num_errors -eq 1 ]]; then
    echo 'OK'
  else
    return 1
  fi
}

codegen-parse() {
  mkdir -p _gen
  local out=_gen/expr_asdl.py
  touch _gen/__init__.py
  asdl-gen mypy examples/expr.asdl > $out
}

# build ASDL schema and run it
pyrun-parse() {
  codegen-parse

  PYTHONPATH="$REPO_ROOT/mycpp:$REPO_ROOT/vendor:$REPO_ROOT" examples/parse.py
}


# TODO: Need a header for this.

readonly HNODE_HEADER='
class Str;
namespace hnode_asdl {
  class hnode__Record;
  class hnode__Leaf;
  enum class color_e;
  typedef color_e color_t;
}

namespace runtime {  // declare
hnode_asdl::hnode__Record* NewRecord(Str* node_type);
hnode_asdl::hnode__Leaf* NewLeaf(Str* s, hnode_asdl::color_t e_color);
extern Str* TRUE_STR;
extern Str* FALSE_STR;

}  // declare namespace runtime
'


# classes and ASDL
translate-parse() {
  # Need this otherwise we get type errors
  codegen-parse

  local snippet='
#include "expr_asdl.h"

// TODO: pretty.Str() turns + into "+", etc.
// This is a good opportunity to use the rest of fastlex.
namespace pretty {
Str* Str(Str* s) {
  return s;
}
}

Str* repr(void* obj) {
  return new Str("TODO: repr()");
}

'
  translate-ordered parse "${HNODE_HEADER}$snippet"  \
    $REPO_ROOT/pylib/cgi.py \
    $REPO_ROOT/asdl/runtime.py \
    $REPO_ROOT/asdl/format.py \
    examples/parse.py 
} 

# Because it depends on ASDL
compile-parse() {
  mkdir -p _gen
  asdl-gen cpp examples/expr.asdl _gen/expr_asdl

  compile-with-asdl parse _gen/expr_asdl.cc ../_devbuild/gen-cpp/hnode_asdl.cc
}

### parse
# Good news!  Parsing is 10x faster.
# 198 ms in C++ vs 1,974 in Python!  Is that because of the method calls?
benchmark-parse() {
  export BENCHMARK=1

  local name=parse

  echo
  echo $'\t[ C++ ]'
  time _bin/$name

  # TODO: Consolidate this with the above.
  # We need 'asdl'
  export PYTHONPATH="$REPO_ROOT/mycpp:$REPO_ROOT"

  echo
  echo $'\t[ Python ]'
  time examples/${name}.py
}

#
# Other
#

translate-modules() {
  local raw=_gen/modules_raw.cc
  local out=_gen/modules.cc

  ( source _tmp/mycpp-venv/bin/activate
    PYTHONPATH=$MYPY_REPO ./mycpp_main.py \
      testpkg/module1.py testpkg/module2.py examples/modules.py > $raw
  )
  filter-cpp modules $raw > $out
  wc -l $raw $out
}

# TODO: Get rid of translate-ordered
translate-asdl-generated() {
  translate-ordered asdl_generated '#include "expr_asdl.h"' \
    $REPO_ROOT/asdl/runtime.py \
    $REPO_ROOT/asdl/format.py \
    examples/asdl_generated.py
} 

lexer-main() {
  local name='lexer_main'
  PYTHONPATH=$REPO_ROOT examples/lexer_main.py
  #mypy --py2 --strict examples/$name.py

  local snippet='
#include "id_kind_asdl.h"  // syntax.asdl depends on this
using id_kind_asdl::Id_t;  // TODO: proper ASDL modules 

#include "types_asdl.h"
#include "syntax_asdl.h"

#include "id.h"
#include "osh-types.h"
#include "osh-lex.h"

// TODO: This is already added elsewhere
#include "mylib.h"

// Hack for now.  Every sum type should have repr()?
Str* repr(syntax_asdl::source_t* obj) {
  return new Str("TODO");
}

// Stub
void p_die(Str* fmt, syntax_asdl::token* blame_token) {
  throw AssertionError();
}

namespace match {

using types_asdl::lex_mode_t;

Tuple2<Id_t, int>* OneToken(lex_mode_t lex_mode, Str* line, int start_pos) {
  int id;
  int end_pos;
  // TODO: get rid of these casts
  MatchOshToken(static_cast<int>(lex_mode),
                reinterpret_cast<const unsigned char*>(line->data_),
                line->len_, start_pos, &id, &end_pos);
  return new Tuple2<Id_t, int>(static_cast<Id_t>(id), end_pos);
}

}
'
  translate-ordered lexer_main "$snippet" \
    $REPO_ROOT/asdl/runtime.py \
    $REPO_ROOT/frontend/reader.py \
    $REPO_ROOT/core/alloc.py \
    $REPO_ROOT/frontend/lexer.py \
    examples/lexer_main.py

  compile-with-asdl $name
}

# TODO: syntax_asdl is used.  Hm.
# So we have to translate tha tfile and include it.
alloc-main() {
  local name='alloc_main'
  #mypy --py2 --strict examples/$name.py

  PYTHONPATH=$REPO_ROOT examples/alloc_main.py
 
  # NOTE: We didn't import source_e because we're using isinstance().
  local snippet='
#include "id_kind_asdl.h"  // syntax.asdl depends on this
using id_kind_asdl::Id_t;  // TODO: proper ASDL modules 
#include "syntax_asdl.h"

// Hack for now.  Every sum type should have repr()?
Str* repr(syntax_asdl::source_t* obj) {
  return new Str("TODO");
}
'
  translate-ordered alloc_main "${HNODE_HEADER}$snippet" \
    $REPO_ROOT/asdl/runtime.py \
    $REPO_ROOT/core/alloc.py \
    examples/alloc_main.py

  local out=_gen/syntax_asdl
  asdl-gen cpp ../frontend/syntax.asdl $out

  compile-with-asdl alloc_main \
    _gen/syntax_asdl.cc \
    ../_devbuild/gen-cpp/hnode_asdl.cc \
    ../_devbuild/gen-cpp/id_kind_asdl.cc
} 
