#!/usr/bin/env bash
#
# Test that we pass ASAN.  Spec tests and benchmarks should do this too.
#
# Usage:
#   test/asan.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

# Check that we don't have any leaks!
soil-run() {
  ninja _bin/cxx-asan/osh

  OILS_GC_ON_EXIT=1 _bin/cxx-asan/osh --version

  OILS_GC_ON_EXIT=1 _bin/cxx-asan/osh -c 'echo hi'
}

cpython-smoke() {
  ### Similar to what benchmarks do

  local bin=_bin/cxx-asan/osh
  local dir=_tmp/cpython-smoke

  ninja $bin

  mkdir -p $dir

  pushd $dir

  # Run CPython configure with ASAN
  $REPO_ROOT/$bin $REPO_ROOT/Python-2.7.13/configure

  popd
}

"$@"
