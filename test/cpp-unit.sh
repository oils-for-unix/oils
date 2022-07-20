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
  ./NINJA_config.py

  # uses Ninja to run (cxx, testgc) variant.  Could also run (clang, ubsan),
  # which finds more bugs.
  mycpp/test.sh soil-run

  cpp/test.sh pre-build
  cpp/test.sh unit

  # Relies on same pre-build
  build/codegen.sh test-generated-code

  asdl/test.sh unit
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
