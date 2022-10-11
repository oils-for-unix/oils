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

pre-build() {
  # TODO: Folding tests into Ninja would get rid of ad hoc deps

  build/py.sh fastmatch
  build/cpp.sh gen-asdl  # unit tests depend on id_kind_asdl.h, etc.

  # TODO: Make a target for this
  ninja _gen/frontend/arg_types.{h,cc}
  ninja _gen/frontend/id_kind.asdl.{h,cc}
}

readonly LEAKY_FLAG_SPEC_SRC=(
    cpp/leaky_flag_spec_test.cc
    cpp/leaky_frontend_flag_spec.cc
    _gen/frontend/arg_types.cc

    # TODO: Remove CPP_UNIT_TEST and fix this
    # prebuilt/frontend/args.mycpp.cc

    "${GC_RUNTIME[@]}"
)

leaky-flag-spec-test() {
  ### Test generated code

  local compiler=${1:-cxx}
  local variant=${2:-dbg}

  local bin=_bin/$compiler-$variant/cpp/leaky_flag_spec_test
  mkdir -p $(dirname $bin)

  # -D CPP_UNIT_TEST is to disable #include prebuilt/...
  compile_and_link $compiler $variant '-D CPP_UNIT_TEST' $bin \
    "${LEAKY_FLAG_SPEC_SRC[@]}"

  run-test-bin $bin
}

readonly LEAKY_TEST_SRC=(
    cpp/leaky_binding_test.cc
    cpp/leaky_core.cc
    cpp/leaky_frontend_match.cc
    cpp/leaky_libc.cc
    cpp/leaky_osh.cc
    cpp/leaky_stdlib.cc
    cpp/leaky_pylib.cc
    "${GC_RUNTIME[@]}"
)

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

# TODO:
#
# - These tests can use Ninja dependencies with -M
#   - separate all the files
# - Put logs in _test/
# - Make HTML links to all the logs
# - Add coverage report

unit() {
  ### Run by test/cpp-unit.sh

  # Run Ninja-based tests
  run-one-test leaky_core_test '' ''
  run-one-test leaky_core_test '' asan

  #gc-binding-test '' gcevery
  run-one-test gc_binding_test '' gcevery

  leaky-binding-test '' ''
  leaky-binding-test '' asan

  # Has generated code
  leaky-flag-spec-test '' ''
  leaky-flag-spec-test '' asan
}

coverage() {
  pre-build

  run-one-test leaky_core_test clang coverage
  run-one-test gc_binding_test clang coverage

  leaky-binding-test clang coverage
  leaky-flag-spec-test clang coverage

  local out_dir=_test/clang-coverage/cpp
  test/coverage.sh html-report $out_dir cpp
}

"$@"
