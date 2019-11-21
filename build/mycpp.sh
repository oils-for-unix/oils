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

CPPFLAGS='-std=c++11 -Wall -O2 -g -ferror-limit=1000'

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

EOF

  cat "$@"

  cat <<EOF
int main(int argc, char **argv) {
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
  echo '// osh_parse: TODO'

  echo "$PGEN2_DEMO_PREAMBLE"
}

osh-parse() {
  local name=${1:-osh_parse}

  local tmp=_tmp/mycpp
  mkdir -p $tmp

  local raw=$tmp/${name}_raw.cc 

  #if false; then
  if true; then
    mycpp $raw bin/$name.py "${PGEN2_DEMO_FILES[@]}"
  fi

  local cc=$tmp/$name.cc

  { osh-parse-preamble 
    cpp-skeleton $name $raw 
  } > $cc

  # TODO:
  compile $tmp/$name $cc \
    mycpp/mylib.cc \
    cpp/frontend_match.cc \
    cpp/asdl_pretty.cc \
    cpp/osh_arith_spec.cc \
    _devbuild/gen-cpp/syntax_asdl.cc \
    _devbuild/gen-cpp/hnode_asdl.cc \
    _devbuild/gen-cpp/id_kind_asdl.cc \
    _devbuild/gen-cpp/lookup.cc

  # Run it
  $tmp/$name
}

"$@"
