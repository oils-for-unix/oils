#!/usr/bin/env bash
#
# Run C++ unit tests.
#
# Usage:
#   test/cpp-unit.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/mycpp.sh  # for compile function

# Copied from devtools/release.sh tarball-build-deps
# for the dev-minimal toil task to run C++ unit tests
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
    cpp/frontend_flag_spec.cc \
    cpp/frontend_match.cc \
    cpp/libc.cc \
    cpp/osh_bool_stat.cc \
    mycpp/mylib.cc
)

cpp-unit-tests-asan() {
  ### Run unit tests in the cpp/ dir

  local bin=_bin/unit_tests.asan
  mkdir -p _bin
  compile $bin -D CPP_UNIT_TEST "${UNIT_TESTS_SRC[@]}"

  $bin "$@"
}

cpp-unit-tests() {
  ### Run unit tests with dumb allocator
  # Exposes allocator alignment issues

  local bin=_bin/unit_tests.dbg  # can't be ASAN; it has its own allocator
  mkdir -p _bin

  compile $bin -D CPP_UNIT_TEST -D DUMB_ALLOC \
    "${UNIT_TESTS_SRC[@]}" \
    cpp/dumb_alloc.cc

  #gdb --args $bin "$@"
  $bin "$@"
}

mycpp-unit-tests() {
  ### Run unit tests in the mycpp/ dir

  pushd mycpp
  set -x
  ./run.sh mylib-test
  ./run.sh mylib2-test
  ./run.sh gc-heap-test
  ./run.sh gc-stress-test
  ./run.sh my-runtime-test
  ./demo.sh target-lang

  # Note: we also have square_heap and gc_heap
  popd
}

all() {
  build/codegen.sh ast-id-lex  # id.h, osh-types.h, osh-lex.h
  build/codegen.sh flag-gen-cpp  # _build/cpp/arg_types.h
  build/dev.sh oil-asdl-to-cpp  # unit tests depend on id_kind_asdl.h, etc.

  cpp-unit-tests
  cpp-unit-tests-asan

  mycpp-unit-tests

  asdl/run.sh gen-cpp-test
  asdl/run.sh gc-test  # integration between ASDL and the GC heap
}

"$@"
