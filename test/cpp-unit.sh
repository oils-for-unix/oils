#!/usr/bin/env bash
#
# Run C++ unit tests.
#
# Usage:
#   test/cpp-unit.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source soil/common.sh  # find-dir-html

all-tests() {
  ./NINJA-config.sh

  # uses Ninja to run (cxx, gcevery) variant.  Could also run (clang, ubsan),
  # which finds more bugs.
  mycpp/TEST.sh soil-run

  cpp/TEST.sh pre-build
  cpp/TEST.sh unit

  # Relies on same pre-build
  build/TEST.sh all

  asdl/TEST.sh unit
}

soil-run() {
  set +o errexit
  $0 all-tests
  local status=$?
  set -o errexit

  # Logs in _test/cxx-asan, etc.
  find-dir-html _test cpp-unit

  return $status
}

"$@"
