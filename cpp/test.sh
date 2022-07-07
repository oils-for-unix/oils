#!/usr/bin/env bash
#
# Run tests in this directory.
#
# Usage:
#   cpp/test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source cpp/NINJA-steps.sh  # for compile_and_link function

# https://github.com/google/sanitizers/wiki/AddressSanitizerLeakSanitizer
export ASAN_OPTIONS='detect_leaks=0'

readonly LEAKY_TEST_SRC=(
    cpp/leaky_binding_test.cc \
    cpp/core_pyos_leaky.cc \
    cpp/core_pyutil_leaky.cc \
    cpp/frontend_match_leaky.cc \
    cpp/libc_leaky.cc \
    cpp/osh_bool_stat_leaky.cc \
    cpp/posix_leaky.cc \
    cpp/pylib_os_path_leaky.cc \
    mycpp/mylib_leaky.cc
)

readonly LEAKY_FLAG_SPEC_SRC=(
    cpp/leaky_flag_spec_test.cc \
    _build/cpp/arg_types.cc \
    cpp/frontend_flag_spec_leaky.cc \
    mycpp/mylib_leaky.cc
)

leaky-flag-spec-test() {
  ### Test generated code

  local dir=_bin/cxx-dbg/cpp
  mkdir -p $dir

  local bin=$dir/leaky_flag_spec_test

  local more_cxx_flags='-D LEAKY_BINDINGS -D CPP_UNIT_TEST -D DUMB_ALLOC' 
  compile_and_link cxx dbg "$more_cxx_flags" $bin \
    "${LEAKY_FLAG_SPEC_SRC[@]}" cpp/dumb_alloc_leaky.cc

  $bin "$@"
}

# TODO:
#
# - Fold variants of leaky_binding_test and gc_binding_test into Ninja
#   - And add cxx-ubsan and clang-coverage -- with HTML output
# - Problem: We don't have fine-grained dependencies for ASDL
#
# Possible solution is to factor into:
#
# build/cpp.sh gen-cpp
# build/cpp.sh all
#
# And then any time a Python source file changes (_build/app-deps), you do the
# whole build/cpp.sh gen-cpp?


leaky-binding-test-asan() {
  local dir=_bin/cxx-asan/cpp
  mkdir -p $dir

  local bin=$dir/leaky_binding_test

  compile_and_link cxx asan '-D LEAKY_BINDINGS -D CPP_UNIT_TEST' $bin \
    "${LEAKY_TEST_SRC[@]}"

  $bin "$@"
}

leaky-binding-test() {
  ### Test hand-written code

  local dir=_bin/cxx-dbg/cpp
  mkdir -p $dir

  local bin=$dir/leaky_binding_test

  # dumb_alloc_leaky.cc exposes allocator alignment issues?

  local more_cxx_flags='-D LEAKY_BINDINGS -D CPP_UNIT_TEST -D DUMB_ALLOC' 
  compile_and_link cxx dbg "$more_cxx_flags" $bin \
    "${LEAKY_TEST_SRC[@]}" cpp/dumb_alloc_leaky.cc

  $bin "$@"
}

readonly GC_TEST_SRC=(
    cpp/gc_binding_test.cc
    mycpp/gc_heap.cc
)

gc-binding-test() {
  local leaky_mode=${1:-}

  local out_dir=_bin/cxx-testgc/cpp
  mkdir -p $out_dir

  local more_cxx_flags='-D DUMB_ALLOC'  # do we need this?
  if test -n "$leaky_mode"; then
    # LEAKY_BINDINGS is in the qsn_qsn.h header; LEAKY_TEST_MODE is gc_binding_test.cc
    more_cxx_flags+=' -D LEAKY_BINDINGS -D LEAKY_TEST_MODE'
  fi

  local bin=$out_dir/gc_binding_test${leaky_mode}
  compile_and_link cxx testgc "$more_cxx_flags" $bin \
    "${GC_TEST_SRC[@]}" cpp/dumb_alloc_leaky.cc

  $bin "$@"
}

all-gc-binding-test() {
  gc-binding-test        # normal GC mode
  gc-binding-test '.LEAKY'  # test in leaky mode too
}

unit() {
  ### Run by test/cpp-unit.sh

  # Generated code
  leaky-flag-spec-test

  leaky-binding-test
  leaky-binding-test-asan

  all-gc-binding-test
}

"$@"
