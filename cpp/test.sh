#!/usr/bin/env bash
#
# Usage:
#   ./test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source cpp/NINJA-steps.sh  # for compile_and_link function

# https://github.com/google/sanitizers/wiki/AddressSanitizerLeakSanitizer
export ASAN_OPTIONS='detect_leaks=0'

readonly LEAKY_TEST_SRC=(
    cpp/leaky_binding_test.cc \
    _build/cpp/arg_types.cc \
    cpp/core_pyos.cc \
    cpp/core_pyutil.cc \
    cpp/frontend_flag_spec.cc \
    cpp/frontend_match.cc \
    cpp/libc.cc \
    cpp/osh_bool_stat.cc \
    cpp/posix.cc \
    cpp/pylib_os_path.cc \
    mycpp/mylib_leaky.cc  # TODO: port to mylib2!
)

# Note: It would be nice to fold these 2 variants into Ninja, but we don't have
# fine-grained dependencies for say _build/cpp/arg_types.cc and
# cpp/frontend_flag_spec.cc.
#
# Ditto with the tests in asdl/test.sh.

leaky-binding-test-asan() {
  local dir=_bin/cxx-asan/cpp
  mkdir -p $dir

  local bin=$dir/leaky_binding_test

  compile_and_link cxx asan '-D CPP_UNIT_TEST' $bin \
    "${LEAKY_TEST_SRC[@]}"

  $bin "$@"
}

leaky-binding-test() {
  local dir=_bin/cxx-dbg/cpp
  mkdir -p $dir

  local bin=$dir/leaky_binding_test

  # dumb_alloc.cc exposes allocator alignment issues?

  local more_cxx_flags='-D CPP_UNIT_TEST -D DUMB_ALLOC' 
  compile_and_link cxx dbg "$more_cxx_flags" $bin \
    "${LEAKY_TEST_SRC[@]}" cpp/dumb_alloc.cc

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
    "${GC_TEST_SRC[@]}" cpp/dumb_alloc.cc

  $bin "$@"
}

all-gc-binding-test() {
  gc-binding-test        # normal GC mode
  gc-binding-test '.LEAKY'  # test in leaky mode too
}

unit() {
  ### Run by test/cpp-unit.sh

  leaky-binding-test
  leaky-binding-test-asan

  all-gc-binding-test
}

"$@"
