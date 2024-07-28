# examples.sh: Hooks for specific files

# COPIED FROM DEFUNCT run.sh.  Because some examples require it.  NOT
# TESTED.  TODO: Delete after it runs under Ninja.

# -I with ASDL files.
compile-with-asdl() {
  local name=$1
  local variant=$2
  local src=_gen/$name.cc
  shift 2

  local flags
  case $variant in
    (asan)
      flags="$BASE_CXXFLAGS $ASAN_FLAGS"
      ;;
    (opt)
      flags="$BASE_CXXFLAGS -O2 -g"
      ;;
    (*)
      flags="$BASE_CXXFLAGS"
      ;;
  esac

  # TODO: Use $REPO_ROOT, etc.
  $CXX -o _bin/$name.$variant $flags \
    -I . -I .. -I ../_devbuild/gen -I ../_build/cpp -I _gen -I ../cpp \
    switchy_containers.cc $src "$@" -lstdc++
}

asdl-gen() {
  PYTHONPATH="$REPO_ROOT:$REPO_ROOT/vendor" $REPO_ROOT/asdl/asdl_main.py "$@"
}

# Type check, with some relaxations for Oil
typecheck-oil() {
  local name=$1
  local flags='--no-strict-optional'

  MYPYPATH="$REPO_ROOT:$REPO_ROOT/native" \
    mypy --py2 --strict $flags examples/$name.py | tee _tmp/err.txt
}

#
# examples/varargs
#

translate-varargs() {
  # Need this otherwise we get type errors
  codegen-parse

  local snippet='
#include "leaky_preamble.h"
#include "asdl_runtime.h"

'
  translate-ordered varargs "$snippet"  \
    $REPO_ROOT/asdl/runtime.py \
    examples/varargs.py
} 

compile-varargs() {
  local variant=$1
  # need -I flag
  compile-with-asdl varargs $variant
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

  # TODO: This is similar to prebuilt/translate.sh ASDL_FILES
  translate-ordered parse ''  \
    $REPO_ROOT/pylib/cgi.py \
    $REPO_ROOT/asdl/runtime.py \
    $REPO_ROOT/asdl/format.py \
    $REPO_ROOT/core/ansi.py \
    $REPO_ROOT/data_lang/j8_lite.py \
    examples/parse.py 
} 

# Because it depends on ASDL
compile-parse() {
  local variant=$1
  mkdir -p _gen
  asdl-gen cpp examples/expr.asdl _gen/expr_asdl

  compile-with-asdl parse $variant \
    _gen/expr_asdl.cc \
    ../_gen/asdl/hnode.asdl.cc
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

lexer-main() {
  local variant=${1:-opt}

  local name='lexer_main'
  PYTHONPATH=$REPO_ROOT examples/lexer_main.py
  #mypy --py2 --strict examples/$name.py

  local snippet='
#include "id_kind_asdl.h"  // syntax.asdl depends on this
using id_kind_asdl::Id_t;  // TODO: proper ASDL modules 

#include "syntax_asdl.h"
#include "types_asdl.h"

//#include "match.h"

#include "mycpp/runtime.h"

// Stub
void p_die(Str* s, syntax_asdl::Token* blame_token) {
  throw AssertionError();
}

// Hack for now.  Every sum type should have repr()?
Str* repr(syntax_asdl::source_t* obj) {
  return StrFromC("TODO");
}
'
  translate-ordered lexer_main "$snippet" \
    $REPO_ROOT/asdl/runtime.py \
    $REPO_ROOT/frontend/reader.py \
    $REPO_ROOT/core/alloc.py \
    $REPO_ROOT/frontend/lexer.py \
    examples/lexer_main.py

  compile-with-asdl $name $variant # ../cpp/match.cc
}

#
# alloc_main
#

typecheck-alloc_main() {
  typecheck-oil alloc_main
}

# TODO: pyrun-alloc_main could set PYTHONPATH for syntax_asdl

compile-alloc_main() {
  local variant=${1:-opt}
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
  return StrFromC("TODO");
}
'
  translate-ordered alloc_main "$snippet" \
    $REPO_ROOT/asdl/runtime.py \
    $REPO_ROOT/core/alloc.py \
    examples/alloc_main.py

  local out=_gen/syntax_asdl
  asdl-gen cpp ../frontend/syntax.asdl $out

  compile-with-asdl alloc_main $variant \
    _gen/syntax_asdl.cc \
    ../_gen/asdl/hnode.asdl.cc \
    ../_gen/frontend/id_kind.asdl.cc
} 

#
# pgen2_demo
#

# build ASDL schema and run it
pyrun-pgen2_demo() {
  #codegen-pgen2_demo
  pushd ..
  build/py.sh demo-grammar
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
  $REPO_ROOT/ysh/expr_parse.py 
  $REPO_ROOT/ysh/expr_to_ast.py 
)

readonly PGEN2_DEMO_FILES=("${FILES[@]}")

# NOTE: Doesn't compile anymore.  Moved onto bin/osh_parse.py
translate-pgen2_demo() {
  local name='pgen2_demo'

  translate-ordered $name "$(cat ../cpp/leaky_preamble.h)" \
    "${PGEN2_DEMO_FILES[@]}" examples/$name.py

  compile-pgen2_demo
} 

compile-pgen2_demo() {
  local variant=$1
  local name='pgen2_demo'

  compile-with-asdl $name $variant \
    ../cpp/leaky_frontend_match.cc \
    ../cpp/leaky_osh_arith_parse.cc \
    ../_devbuild/gen-cpp/syntax_asdl.cc \
    ../_devbuild/gen-cpp/hnode_asdl.cc \
    ../_devbuild/gen-cpp/id_kind_asdl.cc \
    ../_devbuild/gen-cpp/lookup.cc
}
