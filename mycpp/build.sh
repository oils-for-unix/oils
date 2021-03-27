#!/usr/bin/env bash
#
# Entry points for services/toil-worker.sh, and wrappers around Ninja.
#
# Usage:
#   ./build.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(dirname $(readlink -f $0))
readonly REPO_ROOT=$THIS_DIR/..

source $THIS_DIR/common.sh  # MYPY_REPO
source $REPO_ROOT/services/common.sh  # find-dir-html

osh-eval() {
  export MYPY_REPO  # build/mycpp.sh uses this

  build/dev.sh oil-cpp
}

all-ninja() {
  # mycpp_main.py needs to find it
  export MYPY_REPO
  # Don't use clang for benchmarks.
  export CXX=c++

  cd $THIS_DIR
  ./build_graph.py

  set +o errexit

  # includes non-essential stuff like type checking alone, stripping
  ninja all
  local status=$?
  set -o errexit

  find-dir-html _ninja

  # Now we want to zip up
  return $status
}

examples() {
  # invoked by services/toil-worker.sh
  all-ninja
}

run-for-release() {
  # invoked by devtools/release.sh

  rm --verbose -r -f _ninja
  all-ninja

  # Note: harness.sh benchmark-all creates ../_tmp/mycpp-examples/raw/times.tsv
  # It compares C++ and Python.
  #
  # We have _ninja/benchmark-table.tsv instead
}

#
# Utilities
#

config() {
  ./build_graph.py
  cat build.ninja
}

clean() {
  rm --verbose -r -f _ninja
}

"$@"
