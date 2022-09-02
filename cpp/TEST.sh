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
source cpp/NINJA-steps.sh  # for compile_and_link function
source mycpp/common.sh
source mycpp/ninja.sh

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

  local dir=_bin/$compiler-$variant/cpp
  mkdir -p $dir
  local bin=$dir/leaky_flag_spec_test

  # -D CPP_UNIT_TEST is to disable #include _build/cpp/osh_eval.h
  compile_and_link $compiler $variant '-D CPP_UNIT_TEST' $bin \
    "${LEAKY_FLAG_SPEC_SRC[@]}" cpp/dumb_alloc.cc

  run-test $bin $compiler $variant
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

  local dir=$REPO_ROOT/_bin/$compiler-$variant/cpp
  mkdir -p $dir
  local bin=$dir/leaky_binding_test

  # dumb_alloc.cc exposes allocator alignment issues?

  compile_and_link $compiler $variant '' $bin \
    "${LEAKY_TEST_SRC[@]}" cpp/dumb_alloc.cc

  local tmp_dir=_tmp/leaky-binding-test
  rm -r -f -v $tmp_dir
  mkdir -p $tmp_dir
  pushd $tmp_dir >/dev/null

  # to test glob()
  touch {foo,bar,baz}.testdata

  # TODO: we need a way to pass -t here
  run-test $bin $compiler $variant
  popd >/dev/null
}

readonly GC_TEST_SRC=(
    cpp/gc_binding_test.cc
    "${GC_RUNTIME[@]}"
)

gc-binding-test() {
  local compiler=${1:-cxx}
  local variant=${2:-dbg}

  local out_dir=_bin/$compiler-$variant/cpp
  mkdir -p $out_dir

  local bin=$out_dir/gc_binding_test

  compile_and_link $compiler $variant '' $bin \
    "${GC_TEST_SRC[@]}"

  run-test $bin $compiler $variant
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

  gc-binding-test '' gcevery

  # Has generated code
  leaky-flag-spec-test '' ''
  leaky-flag-spec-test '' asan

  leaky-binding-test '' ''
  leaky-binding-test '' asan
}

coverage() {
  pre-build

  gc-binding-test clang coverage
  leaky-flag-spec-test clang coverage
  leaky-binding-test clang coverage

  local out_dir=_test/clang-coverage/cpp
  test/coverage.sh html-report $out_dir cpp
}

"$@"
