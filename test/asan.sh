#!/usr/bin/env bash
#
# Test that we pass ASAN.  Spec tests and benchmarks should do this too.
#
# Usage:
#   test/asan.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Check that we don't have any leaks!
soil-run() {
  ninja _bin/cxx-asan/osh

  OILS_GC_ON_EXIT=1 _bin/cxx-asan/osh --version

  OILS_GC_ON_EXIT=1 _bin/cxx-asan/osh -c 'echo hi'
}

"$@"
