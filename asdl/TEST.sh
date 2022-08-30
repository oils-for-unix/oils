#!/usr/bin/env bash
#
# Tests for ASDL.
#
# Usage:
#   asdl/TEST.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/common.sh  # BASE_CXXFLAGS, etc.
source cpp/NINJA-steps.sh  # compile_and_link
source mycpp/ninja.sh  # OLDSTL_RUNTIME, etc.
source devtools/common.sh  # mypy_, etc.

CPPFLAGS="$BASE_CXXFLAGS -g -fsanitize=address"  # for debugging tests

# Could we turn on the leak detector for the GC tests?
export ASAN_OPTIONS='detect_leaks=0'

asdl-main() {
  PYTHONPATH='.:vendor/' asdl/asdl_main.py "$@"
}

readonly GEN_DIR='_gen/asdl'

gen-cpp-test() {
  local compiler=${1:-cxx}
  local variant=${1:-asan}

  local bin_dir="_bin/$compiler-$variant/asdl"

  mkdir -p $GEN_DIR $bin_dir

  local prefix=$GEN_DIR/typed_arith_asdl
  asdl-main cpp asdl/examples/typed_arith.asdl $prefix

  local prefix2=$GEN_DIR/demo_lib_asdl
  asdl-main cpp asdl/examples/demo_lib.asdl $prefix2

  local prefix3=$GEN_DIR/typed_demo_asdl
  asdl-main cpp asdl/examples/typed_demo.asdl $prefix3

  wc -l $prefix* $prefix2*

  local bin=$bin_dir/gen_cpp_test

  compile_and_link $compiler $variant '-D OLDSTL_BINDINGS' $bin \
    asdl/gen_cpp_test.cc \
    prebuilt/asdl/runtime.mycpp.cc \
    "${OLDSTL_RUNTIME[@]}" \
    $GEN_DIR/typed_arith_asdl.cc \
    $GEN_DIR/typed_demo_asdl.cc 

  local log_dir="_test/$compiler-$variant/asdl"
  mkdir -p $log_dir
  local log="$log_dir/gen_cpp_test.log"
  log "RUN $bin > $log"
  $bin "$@" > "$log"
}

gc-test() {
  local compiler=${1:-cxx}
  local variant=${1:-asan}

  # TODO: remove this after it works with the garbage collector!
  export ASAN_OPTIONS='detect_leaks=0'

  # for hnode_asdl.h
  # TODO: move this into Ninja.  Redundant with cpp/TEST.sh pre-build
  build/cpp.sh gen-asdl

  local bin_dir=_bin/$compiler-$variant/asdl
  mkdir -p $GEN_DIR $bin_dir

  local prefix2=$GEN_DIR/demo_lib_asdl
  asdl-main cpp asdl/examples/demo_lib.asdl $prefix2

  local prefix3=$GEN_DIR/typed_demo_asdl
  asdl-main cpp asdl/examples/typed_demo.asdl $prefix3

  local bin=$bin_dir/gc_test

  # uses typed_arith_asdl.h, runtime.h, hnode_asdl.h, asdl_runtime.h
  compile_and_link $compiler $variant '' $bin \
    asdl/gc_test.cc \
    "${GC_RUNTIME[@]}" \
    prebuilt/asdl/runtime.mycpp.cc \
    $GEN_DIR/demo_lib_asdl.cc \
    $GEN_DIR/typed_demo_asdl.cc

  local log_dir="_test/$compiler-$variant/asdl"
  mkdir -p $log_dir
  local log="$log_dir/gc_test.log"
  log "RUN $bin > $log"
  $bin "$@" > "$log"
}

one-asdl-gc() {
  ### Test that an Oil ASDL file can compile by itself

  local name=$1
  shift

  if false; then
    echo ---
    echo "test-one-asdl-gc $name"
    echo ---
  fi

  local bin_dir=_bin/cxx-asan/asdl
  mkdir -p $GEN_DIR $bin_dir

  cat >$GEN_DIR/${name}_asdl_test.cc <<EOF
#include "_build/cpp/${name}_asdl.h"

int main() {
  printf("OK ${name}_asdl_test\\n");
  return 0;
}
EOF

  local bin=$bin_dir/${name}_asdl_test

  compile_and_link cxx asan '' $bin \
    _build/cpp/${name}_asdl.cc \
    prebuilt/asdl/runtime.mycpp.cc \
    "${GC_RUNTIME[@]}" \
    $GEN_DIR/${name}_asdl_test.cc \
    "$@"

  log "RUN $bin"
  $bin
}

all-asdl-gc() {
  ### All ASDL compilation tests

  # Invoke ASDL compiler on everything
  build/cpp.sh gen-asdl

  # Now make sure they can compile

  # syntax.asdl is a 'use' dependency; 'id' is implicit there is no GC variant
  # for id_kind_asdl
  one-asdl-gc runtime _build/cpp/syntax_asdl.cc _build/cpp/id_kind_asdl.cc

  one-asdl-gc syntax _build/cpp/id_kind_asdl.cc
}

unit() {
  ### Run unit tests

  gen-cpp-test
  echo

  gc-test  # integration between ASDL and the GC heap
  echo

  # test each ASDL file on its own, perhaps with the garbage-collected ASDL runtime
  all-asdl-gc
}

#
# Python codegen
#

readonly PY_PATH='.:vendor/'  # note: could consolidate with other scripts

# NOTE: We're testing ASDL code generation with --strict because we might want
# Oil to pass under --strict someday.
typed-demo-asdl() {
  # We want to exclude ONLY pylib.collections_, but somehow --exclude
  # '.*collections_\.py' does not do it.  So --follow-imports=silent.  Tried
  # --verbose too
  typecheck --strict --follow-imports=silent \
    _devbuild/gen/typed_demo_asdl.py asdl/examples/typed_demo.py

  PYTHONPATH=$PY_PATH asdl/examples/typed_demo.py "$@"
}

check-arith() {
  # NOTE: There are still some Any types here!  We don't want them for
  # translation.

  MYPYPATH=. PYTHONPATH=$PY_PATH typecheck --strict --follow-imports=silent \
    asdl/examples/typed_arith_parse.py \
    asdl/examples/typed_arith_parse_test.py \
    asdl/examples/tdop.py
}

typed-arith-asdl() {
  check-arith

  export PYTHONPATH=$PY_PATH
  asdl/examples/typed_arith_parse_test.py

  banner 'parse'
  asdl/examples/typed_arith_parse.py parse '40+2'
  echo

  banner 'eval'
  asdl/examples/typed_arith_parse.py eval '40+2+5'
  echo
}

check-types() {
  build/py.sh py-asdl-examples

  banner 'typed-arith-asdl'
  typed-arith-asdl

  banner 'typed-demo-asdl'
  typed-demo-asdl
}

"$@"
