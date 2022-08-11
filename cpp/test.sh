#!/usr/bin/env bash
#
# Run tests in this directory.
#
# Usage:
#   cpp/test.sh <function name>

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
  # TODO: sort out these deps
  # This is part of build/dev.sh oil-cpp

  build/codegen.sh ast-id-lex  # id.h, osh-types.h, osh-lex.h
  build/codegen.sh flag-gen-cpp  # _build/cpp/arg_types.h
  build/dev.sh oil-asdl-to-cpp  # unit tests depend on id_kind_asdl.h, etc.
  build/dev.sh cpp-codegen
}

readonly LEAKY_FLAG_SPEC_SRC=(
    cpp/leaky_flag_spec_test.cc
    cpp/leaky_frontend_flag_spec.cc
    _build/cpp/arg_types.cc

    "${OLDSTL_RUNTIME[@]}"
)

leaky-flag-spec-test() {
  ### Test generated code

  local compiler=${1:-cxx}
  local variant=${2:-dbg}

  local dir=_bin/$compiler-$variant/cpp
  mkdir -p $dir
  local bin=$dir/leaky_flag_spec_test

  # -D CPP_UNIT_TEST is to disable #include _build/cpp/osh_eval.h
  local more_cxx_flags='-D OLDSTL_BINDINGS -D CPP_UNIT_TEST'
  compile_and_link $compiler $variant "$more_cxx_flags" $bin \
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

    "${OLDSTL_RUNTIME[@]}"
)

leaky-binding-test() {
  ### Test hand-written code

  local compiler=${1:-cxx}
  local variant=${2:-dbg}

  local dir=_bin/$compiler-$variant/cpp
  mkdir -p $dir
  local bin=$dir/leaky_binding_test

  # dumb_alloc.cc exposes allocator alignment issues?

  local more_cxx_flags='-D OLDSTL_BINDINGS' 
  compile_and_link $compiler $variant "$more_cxx_flags" $bin \
    "${LEAKY_TEST_SRC[@]}" cpp/dumb_alloc.cc

  run-test $bin $compiler $variant
}

readonly GC_TEST_SRC=(
    cpp/gc_binding_test.cc
)

gc-binding-test() {
  local compiler=${1:-cxx}
  local variant=${2:-dbg}

  local out_dir=_bin/$compiler-$variant/cpp
  mkdir -p $out_dir

  local bin=$out_dir/gc_binding_test

  local -a runtime
  case $variant in
    (oldstl)
      runtime=( "${OLDSTL_RUNTIME[@]}" )
      ;;
    (*)
      runtime=( "${GC_RUNTIME[@]}" )
      ;;
  esac

  compile_and_link $compiler $variant '' $bin \
    "${GC_TEST_SRC[@]}" "${runtime[@]}"

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
  gc-binding-test '' oldstl
  # leakyasan?

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
