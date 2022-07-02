#!/usr/bin/env bash
#
# Build oil-native.
#
# Usage:
#   build/native.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/..; pwd)
readonly REPO_ROOT

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

# Demo for the oil-native tarball.
# Notes:
# - Does not rely on Ninja, which is for the dev build
# - It shouldn't require 'objcopy'
# - TODO: do this in the Soil 'cpp' task

tarball-demo() {
  mkdir -p _bin

  time _build/oil-native.sh '' '' SKIP_REBUILD

  local bin=_bin/cxx-opt-sh/osh_eval.stripped

  ls -l $bin

  echo
  echo "You can now run $bin.  Example:"
  echo

  set -o xtrace
  $bin -n -c 'echo "hello $name"'
}

#
# Ninja Wrappers
#

soil-run() {
  ### Invoked by soil/worker.sh

  ./NINJA_config.py

  ninja _bin/cxx-dbg/osh_eval \
        _bin/cxx-asan/osh_eval \
        _bin/cxx-opt/osh_eval.stripped
}

osh-eval-smoke() {
  local bin=_bin/cxx-dbg/osh_eval
  ninja $bin
  types/oil-slice.sh demo $bin
}

#
# Utilities
#

config() {
  ./NINJA_config.py
  cat build.ninja
}

clean() {
  ### e.g. to time ninja build
  rm -r -f --verbose _bin _build _test build.ninja

  # _release is for docs
}

gen-oil-native-sh() {
  ./NINJA_config.py shell
  chmod +x _build/oil-native.sh
  ls -l _build/oil-native.sh
}

"$@"
