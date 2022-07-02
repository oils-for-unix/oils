#!/usr/bin/env bash
#
# Run C++ unit tests.
#
# Usage:
#   test/cpp-unit.sh <function name>

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
    mycpp/mylib.cc  # TODO: port to mylib2!
)

# Note: It would be nice to fold these 2 variants into Ninja, but we don't have
# fine-grained dependencies for say _build/cpp/arg_types.cc and
# cpp/frontend_flag_spec.cc.
#
# Ditto with the tests in asdl/test.sh.

leaky-binding-test-asan() {
  local bin=_bin/leaky_binding_test.asan
  mkdir -p _bin

  compile_and_link cxx asan '' $bin -D CPP_UNIT_TEST \
    "${LEAKY_TEST_SRC[@]}"

  $bin "$@"
}

leaky-binding-test() {
  local bin=_bin/leaky_binding_test.dbg  # can't be ASAN; it has its own allocator
  mkdir -p _bin

  # dumb_alloc.cc exposes allocator alignment issues?

  compile_and_link cxx dbg '' $bin -D CPP_UNIT_TEST -D DUMB_ALLOC \
    "${LEAKY_TEST_SRC[@]}" \
    cpp/dumb_alloc.cc

  $bin "$@"
}

readonly GC_TEST_SRC=(
    cpp/gc_binding_test.cc
    mycpp/gc_heap.cc
)

gc-binding-test() {
  local leaky_mode=${1:-}

  local bin=_bin/gc_binding_test${leaky_mode}.dbg  # can't be ASAN; it has its own allocator
  mkdir -p _bin


  local more_flags=''
  if test -n "$leaky_mode"; then
    # LEAKY_BINDINGS is in the qsn_qsn.h header; LEAKY_TEST_MODE is gc_binding_test.cc
    more_flags='-D LEAKY_BINDINGS -D LEAKY_TEST_MODE'
  fi

  # HACK: 
  # cpp/NINJA-steps.sh compile_and_link does -D LEAKY_BINDINGS, so unset it FIRST
  #   to run in GC mode.  Then we might reset it for leaky mode.
  #   also -U NO_GC_HACK
  # compare with mycpp/NINJA-step.sh compile, which only runs in GC mode
  # TODO: move these flags out

    #// -D GC_DEBUG -D GC_VERBOSE \
  compile_and_link cxx dbg '' $bin \
    -U LEAKY_BINDINGS -U NO_GC_HACK \
    -D DUMB_ALLOC \
    -D GC_EVERY_ALLOC -D GC_PROTECT \
    $more_flags \
    "${GC_TEST_SRC[@]}" \
    cpp/dumb_alloc.cc

  $bin "$@"
}

all-gc-binding-test() {
  gc-binding-test        # normal GC mode
  gc-binding-test '.leaky'  # test in leaky mode too
}

all() {
  build/codegen.sh ast-id-lex  # id.h, osh-types.h, osh-lex.h
  build/codegen.sh flag-gen-cpp  # _build/cpp/arg_types.h
  build/dev.sh oil-asdl-to-cpp  # unit tests depend on id_kind_asdl.h, etc.

  leaky-binding-test
  leaky-binding-test-asan

  all-gc-binding-test

  asdl/test.sh gen-cpp-test
  asdl/test.sh gc-test  # integration between ASDL and the GC heap

  # test each ASDL file on its own, perhaps with the garbage-collected ASDL runtime
  asdl/test.sh all-asdl-gc
}

"$@"
