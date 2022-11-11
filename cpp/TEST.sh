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

pre-build() {
  # TODO: fold this into Ninja so it doesn't invalidate build
  build/py.sh fastmatch
}

unit() {
  ### Run unit tests in this dir; used by test/cpp-unit.sh

  run-one-test cpp/gc_binding_test '' gcevery
  run-one-test cpp/core_test '' gcevery

  # Need -D CPP_UNIT_TEST

  run-special-test cpp/leaky_core_test '' ''
  run-special-test cpp/leaky_core_test '' asan

  run-special-test cpp/leaky_flag_spec_test '' ''
  run-special-test cpp/leaky_flag_spec_test '' asan

  # Runs in different dir
  leaky-binding-test '' ''
  leaky-binding-test '' asan
}

coverage() {
  ### Run coverage for this dir

  pre-build

  run-one-test cpp/gc_binding_test clang coverage
  run-one-test cpp/core_test clang coverage

  run-special-test cpp/leaky_core_test clang coverage
  run-special-test cpp/leaky_flag_spec_test clang coverage

  leaky-binding-test clang coverage

  local out_dir=_test/clang-coverage/cpp
  test/coverage.sh html-report $out_dir cpp
}

"$@"
