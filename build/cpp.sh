#!/usr/bin/env bash
#
# Usage:
#   build/cpp.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/common.sh  # CLANGXX

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
