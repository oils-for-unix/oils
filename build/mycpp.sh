#!/bin/bash
#
# Usage:
#   ./mycpp.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh  # for $CLANG_DIR_RELATIVE, $PREPARE_DIR

readonly REPO_ROOT=~/git/oilshell/oil
source mycpp/examples.sh  # for PGEN2_DEMO_PREAMBLE

readonly MYPY_REPO=~/git/languages/mypy

# note: -Weverything is more than -Wall, but too many errors now.
CPPFLAGS='-std=c++11 -Wall -ferror-limit=1000'
CPPFLAGS="$CPPFLAGS -O0 -g"
#CPPFLAGS="$CPPFLAGS -O2"

readonly CXX=$CLANG_DIR_RELATIVE/bin/clang++
#readonly CXX=c++

asdl-demo() {
  build/dev.sh oil-asdl-to-cpp
  $CXX -o _bin/oil_mycpp $CPPFLAGS \
    -I _devbuild/gen-cpp \
    -I _devbuild/gen \
    -I mycpp \
    bin/oil.cc mycpp/mylib.cc -lstdc++

  echo '___'

  _bin/oil_mycpp
}

mycpp() {
  ### Run mycpp (in a virtualenv because it depends on Python 3 / MyPy)

  local out=$1
  shift

  # created by mycpp/run.sh
  ( source mycpp/_tmp/mycpp-venv/bin/activate
    time PYTHONPATH=$MYPY_REPO MYPYPATH=$REPO_ROOT:$REPO_ROOT/native \
      mycpp/mycpp_main.py "$@" > $out
  )
}

example-skeleton() {
  local namespace=$1
  shift

  cat <<EOF
#include "mylib.h"

EOF

  cat "$@"

  # TODO: This should find main(List<str>* argv) in the namespace
  cat <<EOF

int main(int argc, char **argv) {
  $namespace::run_tests();
}
EOF

}

cpp-skeleton() {
  local namespace=$1
  shift

  cat <<EOF
#include "mylib.h"
#include "preamble.h"  // hard-coded stuff

EOF

  cat "$@"

  cat <<EOF
int main(int argc, char **argv) {
  //log("%p", arith_parse::kNullLookup[1].nud);
  auto* args = new List<Str*>();
  for (int i = 0; i < argc; ++i) {
    args->append(new Str(argv[i]));
  }
  $namespace::main(args);
}
EOF

}

compile() {
  local out=$1
  shift

  $CXX $CPPFLAGS \
    -I mycpp \
    -I cpp \
    -I _devbuild/gen-cpp \
    -I _devbuild/gen \
    -o $out \
    "$@" \
    -lstdc++
}

mycpp-demo() {
  ### Translate, compile, and run a program

  local name=${1:-conditional}

  local raw=_tmp/${name}_raw.cc 
  mycpp $raw mycpp/examples/$name.py

  local cc=_tmp/$name.cc
  example-skeleton $name $raw > $cc

  compile _tmp/$name $cc mycpp/mylib.cc

  # Run it
  _tmp/$name
}

osh-parse-preamble() {
  cat <<EOF
// osh_parse.cc: translated from Python by mycpp

EOF
}

compile-osh-parse() {
  local name=${1:-osh_parse}

  compile $TMP/$name $TMP/${name}.cc \
    mycpp/mylib.cc \
    cpp/frontend_match.cc \
    cpp/asdl_pretty.cc \
    cpp/frontend_tdop.cc \
    cpp/osh_arith_parse.cc \
    _devbuild/gen-cpp/syntax_asdl.cc \
    _devbuild/gen-cpp/hnode_asdl.cc \
    _devbuild/gen-cpp/id_kind_asdl.cc \
    _devbuild/gen-cpp/lookup.cc \
    _devbuild/gen-cpp/arith_parse.cc 
  #2>&1 | tee _tmp/compile.log
}

readonly TMP=_tmp/mycpp

# TODO: Conslidate this with types/osh-parse-manifest.txt?
readonly OSH_PARSE_FILES=(
  $REPO_ROOT/asdl/format.py 
  $REPO_ROOT/asdl/runtime.py 

  $REPO_ROOT/core/alloc.py 
  $REPO_ROOT/frontend/reader.py 
  $REPO_ROOT/frontend/lexer.py 
  $REPO_ROOT/pgen2/grammar.py 
  $REPO_ROOT/pgen2/parse.py 
  $REPO_ROOT/oil_lang/expr_parse.py 
  $REPO_ROOT/oil_lang/expr_to_ast.py 

  $REPO_ROOT/pylib/cgi.py
  # join(*p) is a problem
  #$REPO_ROOT/pylib/os_path.py

  $REPO_ROOT/osh/braces.py

  # This has errfmt.Print() which uses *args and **kwargs
  $REPO_ROOT/core/ui.py

  $REPO_ROOT/core/error.py
  $REPO_ROOT/core/main_loop.py

  $REPO_ROOT/osh/word_.py 
  $REPO_ROOT/osh/bool_parse.py 
  $REPO_ROOT/osh/word_parse.py
  $REPO_ROOT/osh/cmd_parse.py 
  $REPO_ROOT/osh/arith_parse.py 
  $REPO_ROOT/osh/tdop.py
  $REPO_ROOT/frontend/parse_lib.py
)

osh-parse() {
  local name=${1:-osh_parse}

  local tmp=$TMP
  mkdir -p $tmp

  local raw=$tmp/${name}_raw.cc 

  #if false; then
  if true; then
    mycpp $raw bin/$name.py "${OSH_PARSE_FILES[@]}"
  fi

  local cc=$tmp/$name.cc

  { osh-parse-preamble 
    cpp-skeleton $name $raw 
  } > $cc

  compile-osh-parse $name
}

run-osh-parse() {
  local code_str=${1:-'echo hi'}

  local name='osh_parse'
  local tmp=$TMP

  strip -o $tmp/${name}.stripped $tmp/$name
  ls -l $tmp

  # Run it
  $tmp/$name -c "$code_str"
}

size-profile() {
  wc -l $TMP/osh_parse.cc
  bloaty -d compileunits $TMP/osh_parse
  echo
  bloaty -d symbols $TMP/osh_parse
}

osh-parse-smoke() {
  local python=${1:-}

  #for file in */*.sh; do
  for file in spec/*.sh; do
    case $file in
      # Exclude _tmp/ etc.
      _*) continue ;;

      # the STDOUT blocks have invalid syntax
      # TODO: Enable this as a separate test of syntax errors
      #spec/*) continue ;;

      # pgen2 not done
      spec/oil-*) continue ;;

      # This has Oil syntax
      test/oil-runtime-errors.sh) continue ;;
    esac

    echo $file
    set +o errexit
    if test -n "$python"; then
      bin/osh -n $file | wc -l
    else
      _tmp/mycpp/osh_parse $file | wc -l
    fi
    set -o errexit
  done
}

# TODO: We need a proper unit test framework
frontend-match-test() {
  local name='frontend_match_test'
  compile $TMP/$name cpp/frontend_match_test.cc cpp/frontend_match.cc mycpp/mylib.cc

  $TMP/$name
}

"$@"
