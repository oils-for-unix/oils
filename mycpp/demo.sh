#!/bin/bash
#
# Usage:
#   ./demo.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(cd $(dirname $0) && pwd)
readonly REPO_ROOT=$(cd $THIS_DIR/.. && pwd)

source $REPO_ROOT/build/common.sh  # for $CLANG_DIR_RELATIVE, $PREPARE_DIR

CPPFLAGS="$CXXFLAGS -O0 -g -fsanitize=address"
export ASAN_OPTIONS='detect_leaks=0'  # like build/mycpp.sh

# Copied from mycpp/run.sh
cpp-compile() {
  local main_cc=$1
  local bin=$2
  shift 2

  mkdir -p _bin
  $CXX -o $bin $CPPFLAGS -I . $main_cc "$@" -lstdc++
}

cpp-compile-run() {
  local main_cc=$1
  shift

  local name=$(basename $main_cc .cc)
  local bin=_bin/$name

  cpp-compile $main_cc $bin "$@"
  $bin
}

square-heap() {
  cpp-compile-run demo/square_heap.cc "$@"
}


"$@"
