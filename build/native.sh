#!/usr/bin/env bash
#
# Build oil-native.
#
# Usage:
#   build/native.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

#
# Wrapper functions that don't use Ninja
#

# Used by devtools/release.sh and devtools/release-native.sh
# This is the demo we're releasing to users!
compile-oil-native() {
  build/native-steps.sh compile-slice osh_eval ''
}

compile-oil-native-asan() {
  build/native-steps.sh compile-slice osh_eval '.asan'
}

compile-oil-native-opt() {
  build/native-steps.sh compile-slice osh_eval '.opt'

  local in=_bin/osh_eval.opt
  local out=$in.stripped
  strip -o $out $in
}

# Demo for the oil-native tarball.
# Notes:
# - This should not rely on Ninja!  Ninja is for the dev build.
# - It should also not require 'objcopy'

tarball-demo() {
  mkdir -p _bin

  time compile-oil-native-opt

  local bin=_bin/osh_eval.opt.stripped

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

  build/native_graph.py

  # TODO: do we need to force a GCC variant?
  ninja _bin/osh_eval.{dbg,opt,opt.stripped,asan}
}

osh-eval-dbg() {
  ### Invoked by build/dev.sh oil-cpp
  build/native_graph.py
  ninja _bin/osh_eval.dbg
}

osh-eval-asan() {
  ### Invoked by test/parse-errors.sh
  build/native_graph.py
  ninja _bin/osh_eval.asan
}

osh-eval-opt() {
  ### Invoked by test/parse-errors.sh
  build/native_graph.py
  ninja _bin/osh_eval.opt.stripped
}

all-ninja() {
  # Don't use clang for benchmarks.
  # export CXX=c++

  build/native_graph.py

  set +o errexit

  # includes non-essential stuff like type checking alone, stripping
  ninja all
  local status=$?
  set -o errexit

  ls -l _bin/

  # Now we want to zip up
  return $status
}

osh-eval-demo() {
  osh-eval-dbg
  types/oil-slice.sh demo _bin/osh_eval.dbg
}

#
# Utilities
#

config() {
  build/native_graph.py
  cat build.ninja
}

"$@"
