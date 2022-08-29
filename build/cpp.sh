#!/usr/bin/env bash
#
# Usage:
#   build/cpp.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/common.sh  # CLANGXX

# Some tests don't express proper dependencies, and need this.
gen-asdl() {
  ninja \
    _build/cpp/hnode_asdl.h \
    _build/cpp/types_asdl.h \
    _build/cpp/runtime_asdl.h \
    _build/cpp/syntax_asdl.h
}

gen-oil-native-sh() {
  PYTHONPATH=. build/NINJA_main.py shell
  chmod +x _build/oil-native.sh
}

all() {
  ./NINJA-config.sh  # Create it for the first time

  gen-oil-native-sh  # script to build it

  #time ninja -j 1 _bin/cxx-dbg/osh_eval
  time ninja _bin/cxx-dbg/osh_eval
  echo

  ls -l _bin/*/osh_eval*
}

compile-quickly() {
  ### For the fast possible development experience

  if test -f "$CLANGXX"; then
    ninja _bin/clang-dbg/osh_eval
  else
    echo ""
    echo " Error: Unable to locate clang at ($CLANGXX)"
    echo ""
    echo "        To install clang at the specified path, run the following commands:"
    echo ""
    echo "        soil/deps-binary.sh download-clang"
    echo "        soil/deps-binary.sh extract-clang"
    echo ""
  fi
}

compiler-trace-build() {
  ### Output _build/obj/clang-dbg/*.json files

  local variant=${1:-dbg}

  # Only clang supports -ftime-trace
  CXXFLAGS='-ftime-trace' ninja _bin/clang-$variant/osh_eval
}

"$@"
