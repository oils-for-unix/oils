#!/usr/bin/env bash
#
# Run tests in this directory.
#
# Usage:
#   cpp/TEST.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
source build/common.sh
source build/ninja-rules-cpp.sh  # for compile_and_link function
source mycpp/ninja.sh
source test/common.sh  # run-test

# https://github.com/google/sanitizers/wiki/AddressSanitizerLeakSanitizer
export ASAN_OPTIONS='detect_leaks=0'

leaky-flag-spec-test() {
  ### Test generated code

  local compiler=${1:-cxx}
  local variant=${2:-dbg}

  # -D CPP_UNIT_TEST
  local bin=_bin/$compiler-$variant-D_CPP_UNIT_TEST/cpp/leaky_flag_spec_test
  ninja $bin

  run-test-bin $bin
}

leaky-binding-test() {
  ### Test hand-written code

  local compiler=${1:-cxx}
  local variant=${2:-dbg}

  local name=leaky_binding_test
  local bin=_bin/$compiler-$variant/cpp/$name
  ninja $bin

  local working_dir=_tmp/leaky-binding-test
  rm -r -f -v $working_dir
  mkdir -p $working_dir

  # to test glob()
  touch $working_dir/{foo,bar,baz}.testdata

  # TODO: we need a way to pass -t here
  run-test-bin $bin $working_dir
}

run-one-test() {
  local name=$1
  local compiler=${2:-cxx}
  local variant=${3:-dbg}

  local bin=_bin/$compiler-$variant/cpp/$name

  ninja $bin

  run-test-bin $bin
}

unit() {
  ### Run unit tests in this dir; used by test/cpp-unit.sh

  build/py.sh fastmatch  # Could fold this into Ninja

  # Run Ninja-based tests
  run-one-test leaky_core_test '' ''
  run-one-test leaky_core_test '' asan

  run-one-test gc_binding_test '' gcevery

  # Runs in different dir
  leaky-binding-test '' ''
  leaky-binding-test '' asan

  # Needs -D CPP_UNIT_TEST
  leaky-flag-spec-test '' ''
  leaky-flag-spec-test '' asan
}

coverage() {
  ### Run coverage for this dir

  build/py.sh fastmatch  # Could fold this into Ninja

  run-one-test leaky_core_test clang coverage
  run-one-test gc_binding_test clang coverage

  leaky-binding-test clang coverage
  leaky-flag-spec-test clang coverage

  local out_dir=_test/clang-coverage/cpp
  test/coverage.sh html-report $out_dir cpp
}

"$@"
