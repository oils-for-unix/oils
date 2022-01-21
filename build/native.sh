#!/usr/bin/env bash
#
# Build oil-native.
#
# Usage:
#   build/native.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(dirname $(readlink -f $0))
readonly REPO_ROOT=$THIS_DIR/..

#source $THIS_DIR/common.sh  # MYPY_REPO
source $REPO_ROOT/soil/common.sh  # find-dir-html

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

soil-run() {
  ### Invoked by soil/worker.sh

  build/native_graph.py

  # TODO: do we need to force a GCC variant?
  ninja _bin/osh_eval.{dbg,opt,opt.stripped,asan}
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

  find-dir-html _bin

  # Now we want to zip up
  return $status
}

#
# Utilities
#

config() {
  build/native_graph.py
  cat build.ninja
}

"$@"
