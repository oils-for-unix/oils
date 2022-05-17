#!/usr/bin/env bash
#
# Build oil-native.
#
# Usage:
#   build/native.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh  # CLANGXX

compile-quickly() {
  ### For the fast possible development experience

  ninja _bin/clang-dbg/osh_eval
}

compiler-trace-build() {
  ### Output _build/obj/clang-dbg/*.json files

  local variant=${1:-dbg}

  # Only clang supports -ftime-trace
  CXXFLAGS='-ftime-trace' ninja _bin/clang-$variant/osh_eval
}

# Demo for the oil-native tarball.
# Notes:
# - This should not rely on Ninja!  Ninja is for the dev build.
# - It should also not require 'objcopy'

tarball-demo() {
  mkdir -p _bin

  time _build/oil-native.sh opt

  local bin=_bin/cxx-opt/osh_eval.stripped

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

  ninja _bin/cxx-dbg/osh_eval \
        _bin/cxx-asan/osh_eval \
        _bin/cxx-opt/osh_eval.stripped
}

all-ninja() {
  # Don't use clang for benchmarks.
  # export CXX=c++

  set +o errexit

  # includes non-essential stuff like type checking alone, stripping
  ninja all
  local status=$?
  set -o errexit

  ls -l _bin/

  # Now we want to zip up
  return $status
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
  build/native_graph.py
  cat build.ninja
}

clean() {
  ### e.g. to time ninja build
  rm -r -f -v _bin/* _build/obj/*
}

gen-oil-native-sh() {
  build/native_graph.py shell
  chmod +x _build/oil-native.sh
  ls -l _build/oil-native.sh
}

"$@"
