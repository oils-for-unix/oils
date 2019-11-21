#!/bin/bash
#
# Usage:
#   ./mycpp.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh  # for $CLANG_DIR_RELATIVE, $PREPARE_DIR

CPPFLAGS='-std=c++11 -Wall -O2 -g'

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

readonly MYPY_REPO=~/git/languages/mypy
readonly REPO_ROOT=~/git/oilshell/oil

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

cpp-skeleton() {
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

compile() {
  local out=$1
  shift

  $CXX $CPPFLAGS \
    -I mycpp \
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
  cpp-skeleton $name $raw > $cc

  compile _tmp/$name $cc mycpp/mylib.cc

  # Run it
  _tmp/$name
}

"$@"
