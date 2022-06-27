#!/usr/bin/env bash
#
# Run C++ unit tests.
#
# Usage:
#   test/cpp-unit.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/native-steps.sh  # for compile_and_link function

# https://github.com/google/sanitizers/wiki/AddressSanitizerLeakSanitizer
export ASAN_OPTIONS='detect_leaks=0'

# Copied from devtools/release.sh tarball-build-deps
# for the 'cpp' toil job
deps() {
  local d1='_deps/re2c-1.0.3'
  if test -d $d1; then
    echo "$d1 exists: skipping re2c"
  else
    build/codegen.sh download-re2c
    build/codegen.sh install-re2c
  fi
}

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

  #gdb --args $bin "$@"

  $bin "$@"
}

all() {
  build/codegen.sh ast-id-lex  # id.h, osh-types.h, osh-lex.h
  build/codegen.sh flag-gen-cpp  # _build/cpp/arg_types.h
  build/dev.sh oil-asdl-to-cpp  # unit tests depend on id_kind_asdl.h, etc.

  # test each ASDL file on its own, perhaps with the garbage-collected ASDL runtime
  build/dev.sh test-all-asdl-gc

  cpp-unit-tests
  cpp-unit-tests-asan

  # TODO: These tests should be built by Ninja.
  asdl/run.sh gen-cpp-test
  asdl/run.sh gc-test  # integration between ASDL and the GC heap
}

"$@"
