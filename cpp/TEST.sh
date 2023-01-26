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

run-test-in-dir() {
  ### Test hand-written code

  local rel_path=$1
  local compiler=${2:-cxx}
  local variant=${3:-dbg}

  local bin=_bin/$compiler-$variant/$rel_path
  ninja $bin

  local working_dir=_tmp/$rel_path
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


readonly -a GOOD_TESTS=(
  cpp/qsn_test
)

readonly -a LEAKY_TESTS=(
)

unit() {
  ### Run unit tests in this dir; used by test/cpp-unit.sh

  # Tests that pass with the garbage collector on.
  # TODO: Move all tests here

  for variant in ubsan gcalways; do
    run-one-test     cpp/obj_layout_test '' $variant

    run-test-in-dir  cpp/core_test '' $variant  # has testdata

    run-one-test     cpp/qsn_test '' $variant
  done

  # Other tests
  for variant in ubsan asan; do
    run-one-test cpp/frontend_flag_spec_test '' $variant

    run-one-test     cpp/frontend_match_test '' $variant

    run-test-in-dir  cpp/libc_test '' $variant  # has testdata

    run-one-test     cpp/osh_test '' $variant

    run-one-test     cpp/pylib_test '' $variant

    run-one-test     cpp/stdlib_test '' $variant
  done
}

data-race-test() {
  ### TODO: Expand this to signal state, and make sure it passes!

  run-one-test cpp/data_race_test '' tsan
}

coverage() {
  ### Run coverage for this dir

  pre-build

  local compiler=clang
  local variant=coverage

  run-one-test     cpp/obj_layout_test $compiler $variant

  run-test-in-dir  cpp/core_test $compiler $variant  # has testdata

  run-one-test     cpp/qsn_test $compiler $variant

  run-one-test cpp/frontend_flag_spec_test $compiler $variant

  run-one-test     cpp/frontend_match_test $compiler $variant

  run-test-in-dir  cpp/libc_test $compiler $variant  # has testdata

  run-one-test     cpp/osh_test $compiler $variant

  run-one-test     cpp/pylib_test $compiler $variant

  run-one-test     cpp/stdlib_test $compiler $variant

  local out_dir=_test/clang-coverage/cpp
  test/coverage.sh html-report $out_dir clang-coverage/cpp 
}

"$@"
