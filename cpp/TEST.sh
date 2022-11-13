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
source test/common.sh  # run-test

run-special-test() {
  ### For tests with -D CPP_UNIT_TEST

  local rel_path=$1
  local compiler=${2:-cxx}
  local variant=${3:-dbg}

  # -D CPP_UNIT_TEST
  local bin=_bin/$compiler-$variant-D_CPP_UNIT_TEST/$rel_path
  ninja $bin

  run-test-bin $bin
}

leaky-binding-test() {
  ### Test hand-written code

  local compiler=${1:-cxx}
  local variant=${2:-dbg}

  local name=binding_test
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

pre-build() {
  # TODO: fold this into Ninja so it doesn't invalidate build
  build/py.sh fastmatch
}

# Tests that pass with the garbage collector on.
# TODO: Move all tests here

readonly -a GOOD_TESTS=(
  cpp/qsn_test
  cpp/core_test
)

readonly -a LEAKY_TESTS=(
  cpp/frontend_match_test
)

unit() {
  ### Run unit tests in this dir; used by test/cpp-unit.sh

  for t in "${GOOD_TESTS[@]}"; do
    run-one-test $t '' ubsan
    run-one-test $t '' gcevery
    # run-one-test $t '' rvroot
  done

  # These don't run with GC_EVERY_ALLOC
  for t in "${LEAKY_TESTS[@]}"; do
    run-one-test $t '' ubsan
  done

  # Need -D CPP_UNIT_TEST
  run-special-test cpp/frontend_flag_spec_test '' ubsan
  run-special-test cpp/frontend_flag_spec_test '' asan
  # Doesn't work
  # run-special-test cpp/frontend_flag_spec_test '' gcevery

  # Runs in different dir
  leaky-binding-test '' ubsan
  leaky-binding-test '' asan
}

data-race-test() {
  ### TODO: Expand this to signal state, and make sure it passes!

  run-one-test cpp/data_race_test '' tsan
}

coverage() {
  ### Run coverage for this dir

  pre-build

  for t in "${GOOD_TESTS[@]}"; do
    run-one-test $t clang coverage
  done

  for t in "${LEAKY_TESTS[@]}"; do
    run-one-test $t clang coverage
  done

  # Need -D CPP_UNIT_TEST
  run-special-test cpp/frontend_flag_spec_test clang coverage

  leaky-binding-test clang coverage

  local out_dir=_test/clang-coverage/cpp
  test/coverage.sh html-report $out_dir cpp
}

"$@"
