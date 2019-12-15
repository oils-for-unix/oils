# examples.sh: Hooks for specific files

# Type check, with some relaxations for Oil
typecheck-oil() {
  local name=$1
  local flags='--no-strict-optional'

  set +o errexit
  MYPYPATH="$REPO_ROOT:$REPO_ROOT/native" \
    mypy --py2 --strict $flags examples/$name.py | tee _tmp/err.txt
  set -o errexit

  # Stupid fastlex error in asdl/pretty.py

  local num_errors=$(grep -v 'Found 1 error in 1 file' _tmp/err.txt | wc -l)
  if [[ $num_errors -eq 1 ]]; then
    echo 'OK'
  else
    return 1
  fi
}

#
# examples/parse
#

typecheck-parse() {
  typecheck-oil parse
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

# classes and ASDL
translate-parse() {
  # Need this otherwise we get type errors
  codegen-parse

  local snippet='
#include "expr_asdl.h"
#include "asdl_pretty.h"

Str* repr(void* obj) {
  return new Str("TODO: repr()");
}

'
  translate-ordered parse "$snippet"  \
    $REPO_ROOT/pylib/cgi.py \
    $REPO_ROOT/asdl/runtime.py \
    $REPO_ROOT/asdl/format.py \
    examples/parse.py 
} 

# Because it depends on ASDL
compile-parse() {
  mkdir -p _gen
  asdl-gen cpp examples/expr.asdl _gen/expr_asdl

  compile-with-asdl parse \
    ../cpp/asdl_pretty.cc \
    _gen/expr_asdl.cc \
    ../_build/cpp/hnode_asdl.cc
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

#include "syntax_asdl.h"

#include "match.h"

// TODO: This is already added elsewhere
#include "mylib.h"

// Stub
void p_die(Str* s, syntax_asdl::token* blame_token) {
  throw AssertionError();
}

// Hack for now.  Every sum type should have repr()?
Str* repr(syntax_asdl::source_t* obj) {
  return new Str("TODO");
}
'
  translate-ordered lexer_main "$snippet" \
    $REPO_ROOT/asdl/runtime.py \
    $REPO_ROOT/frontend/reader.py \
    $REPO_ROOT/core/alloc.py \
    $REPO_ROOT/frontend/lexer.py \
    examples/lexer_main.py

  compile-with-asdl $name ../cpp/match.cc
}

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
  translate-ordered alloc_main "$snippet" \
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

#
# pgen2_demo
#

# build ASDL schema and run it
pyrun-pgen2_demo() {
  #codegen-pgen2_demo
  pushd ..
  build/dev.sh demo-grammar
  popd

  PYTHONPATH="$REPO_ROOT/mycpp:$REPO_ROOT/vendor:$REPO_ROOT" examples/pgen2_demo.py
}

typecheck-pgen2_demo() {
  typecheck-oil pgen2_demo
}

# These files compile
FILES=(
  $REPO_ROOT/asdl/runtime.py 
  $REPO_ROOT/core/alloc.py 
  $REPO_ROOT/frontend/reader.py 
  $REPO_ROOT/frontend/lexer.py 
  $REPO_ROOT/pgen2/grammar.py 
  $REPO_ROOT/pgen2/parse.py 
  $REPO_ROOT/oil_lang/expr_parse.py 
  $REPO_ROOT/oil_lang/expr_to_ast.py 
)

readonly PGEN2_DEMO_FILES=("${FILES[@]}")

# NOTE: Doesn't compile anymore.  Moved onto bin/osh_parse.py
translate-pgen2_demo() {
  local name='pgen2_demo'

  translate-ordered $name "$(cat ../cpp/preamble.h)" \
    "${PGEN2_DEMO_FILES[@]}" examples/$name.py

  compile-pgen2_demo
} 

compile-pgen2_demo() {
  local name='pgen2_demo'

  compile-with-asdl $name \
    ../cpp/frontend_match.cc \
    ../cpp/asdl_pretty.cc \
    ../cpp/osh_arith_parse.cc \
    ../_devbuild/gen-cpp/syntax_asdl.cc \
    ../_devbuild/gen-cpp/hnode_asdl.cc \
    ../_devbuild/gen-cpp/id_kind_asdl.cc \
    ../_devbuild/gen-cpp/lookup.cc
}
