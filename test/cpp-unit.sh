#!/usr/bin/env bash
#
# Run C++ unit tests.
#
# Usage:
#   test/cpp-unit.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

soil-run() {
  ./NINJA_config.py

  # uses Ninja to run (cxx, testgc) variant.  Could also run (clang, ubsan),
  # which finds more bugs.
  mycpp/test.sh soil-run

  cpp/test.sh pre-build
  cpp/test.sh unit

  asdl/test.sh unit
}

"$@"
