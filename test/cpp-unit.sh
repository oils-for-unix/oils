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
  asdl/TEST.sh unit

  core/TEST.sh unit

  cpp/TEST.sh unit

  data_lang/TEST.sh unit

  frontend/TEST.sh unit

  # uses Ninja to run (cxx, gcalways) variant.  Could also run (clang, ubsan),
  # which finds more bugs.
  mycpp/TEST.sh test-runtime

  yaks/TEST.sh unit
}

soil-run() {
  ### Hook for soil/worker.sh

  # Soil only does build/dev.sh minimal, while most devs should do build/dev.sh
  # all, and can run all-tests by itself
  cpp/TEST.sh pre-build

  set +o errexit
  $0 all-tests
  local status=$?
  set -o errexit

  # Logs in _test/cxx-asan, etc.
  find-dir-html _test cpp-unit

  return $status
}

"$@"
