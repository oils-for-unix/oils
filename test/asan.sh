#!/usr/bin/env bash
#
# Test that we pass ASAN.  Spec tests and benchmarks should do this too.
#
# Usage:
#   test/asan.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# TODO: Make this pass!
test-gc-cleanup() {
  ninja _bin/cxx-asan/osh

  OIL_GC_ON_EXIT=1 _bin/cxx-asan/osh --version

  #_bin/cxx-asan/osh -c 'echo hi'
}

"$@"
