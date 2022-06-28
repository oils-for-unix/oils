#!/usr/bin/env bash
#
# Run C++ unit tests.
#
# Usage:
#   test/cpp-unit.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/NINJA-steps.sh  # for compile_and_link function

# https://github.com/google/sanitizers/wiki/AddressSanitizerLeakSanitizer
export ASAN_OPTIONS='detect_leaks=0'

readonly UNIT_TESTS_SRC=(
    cpp/unit_tests.cc \
    _build/cpp/arg_types.cc \
    cpp/core_pyos.cc \
    cpp/core_pyutil.cc \
    cpp/frontend_flag_spec.cc \
    cpp/frontend_match.cc \
    cpp/libc.cc \
    cpp/osh_bool_stat.cc \
    cpp/posix.cc \
    cpp/pylib_os_path.cc \
    mycpp/mylib.cc  # TODO: port to mylib2!
)

# Note: It would be nice to fold these 2 variants into Ninja, but we don't have
# fine-grained dependencies for say _build/cpp/arg_types.cc and
# cpp/frontend_flag_spec.cc.
#
# Ditto with the tests in asdl/test.sh.

cpp-unit-tests-asan() {
  ### Run unit tests in the cpp/ dir

  local bin=_bin/unit_tests.asan
  mkdir -p _bin
  compile_and_link cxx asan $bin -D CPP_UNIT_TEST "${UNIT_TESTS_SRC[@]}"

  $bin "$@"
}

cpp-unit-tests() {
  ### Run unit tests with dumb allocator
  # Exposes allocator alignment issues

  local bin=_bin/unit_tests.dbg  # can't be ASAN; it has its own allocator
  mkdir -p _bin

  compile_and_link cxx dbg $bin -D CPP_UNIT_TEST -D DUMB_ALLOC \
    "${UNIT_TESTS_SRC[@]}" \
    cpp/dumb_alloc.cc

  $bin "$@"
}

all() {
  build/codegen.sh ast-id-lex  # id.h, osh-types.h, osh-lex.h
  build/codegen.sh flag-gen-cpp  # _build/cpp/arg_types.h
  build/dev.sh oil-asdl-to-cpp  # unit tests depend on id_kind_asdl.h, etc.

  cpp-unit-tests
  cpp-unit-tests-asan

  asdl/test.sh gen-cpp-test
  asdl/test.sh gc-test  # integration between ASDL and the GC heap

  # test each ASDL file on its own, perhaps with the garbage-collected ASDL runtime
  asdl/test.sh all-asdl-gc
}

"$@"
