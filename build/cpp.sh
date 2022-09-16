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
    _gen/asdl/hnode.asdl.h \
    _gen/frontend/types.asdl.h \
    _gen/core/runtime.asdl.h \
    _gen/frontend/syntax.asdl.h
}

gen-oil-native-sh() {
  PYTHONPATH=. build/ninja_main.py shell
  chmod +x _build/oil-native.sh
}

all() {
  ./NINJA-config.sh

  # Needed for release tarball
  gen-oil-native-sh

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
    echo "        deps/from-binary.sh download-clang"
    echo "        deps/from-binary.sh extract-clang"
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
