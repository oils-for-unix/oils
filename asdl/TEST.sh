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

source build/common.sh     # BASE_CXXFLAGS, etc.
source cpp/NINJA-steps.sh  # compile_and_link
source devtools/common.sh  # banner
source mycpp/ninja.sh      # GC_RUNTIME
source test/common.sh      # run-test

CPPFLAGS="$BASE_CXXFLAGS -g -fsanitize=address"  # for debugging tests

# Could we turn on the leak detector for the GC tests?
export ASAN_OPTIONS='detect_leaks=0'

asdl-main() {
  PYTHONPATH='.:vendor/' asdl/asdl_main.py "$@"
}

readonly GEN_DIR='_gen/asdl/examples'

gen-cpp-test() {
  local compiler=${1:-cxx}
  local variant=${2:-asan}

  local bin_dir="_bin/$compiler-$variant/asdl"

  mkdir -p $GEN_DIR $bin_dir

  local prefix=$GEN_DIR/typed_arith.asdl
  asdl-main cpp asdl/examples/typed_arith.asdl $prefix

  local prefix2=$GEN_DIR/demo_lib.asdl
  asdl-main cpp asdl/examples/demo_lib.asdl $prefix2

  local prefix3=$GEN_DIR/typed_demo.asdl
  asdl-main cpp asdl/examples/typed_demo.asdl $prefix3

  wc -l $prefix* $prefix2*

  local bin=$bin_dir/gen_cpp_test

  compile_and_link $compiler $variant '' $bin \
    asdl/gen_cpp_test.cc \
    prebuilt/asdl/runtime.mycpp.cc \
    "${GC_RUNTIME[@]}" \
    $GEN_DIR/typed_arith.asdl.cc \
    $GEN_DIR/typed_demo.asdl.cc 

  run-test $bin $compiler $variant
}

gc-test() {
  local compiler=${1:-cxx}
  local variant=${2:-asan}

  # TODO: remove this after it works with the garbage collector!
  export ASAN_OPTIONS='detect_leaks=0'

  # for hnode_asdl.h
  # TODO: move this into Ninja.  Redundant with cpp/TEST.sh pre-build
  build/cpp.sh gen-asdl

  local bin_dir=_bin/$compiler-$variant/asdl
  mkdir -p $GEN_DIR $bin_dir

  local prefix2=$GEN_DIR/demo_lib.asdl
  asdl-main cpp asdl/examples/demo_lib.asdl $prefix2

  local prefix3=$GEN_DIR/typed_demo.asdl
  asdl-main cpp asdl/examples/typed_demo.asdl $prefix3

  local bin=$bin_dir/gc_test

  # uses typed_arith_asdl.h, runtime.h, hnode_asdl.h, asdl_runtime.h
  compile_and_link $compiler $variant '' $bin \
    asdl/gc_test.cc \
    "${GC_RUNTIME[@]}" \
    prebuilt/asdl/runtime.mycpp.cc \
    $GEN_DIR/demo_lib.asdl.cc \
    $GEN_DIR/typed_demo.asdl.cc

  run-test $bin $compiler $variant
}

one-asdl-gc() {
  ### Test that an Oil ASDL file can compile by itself

  local compiler=$1
  local variant=$2
  local rel_path=$3
  shift 3

  local name
  name=$(basename $rel_path)

  if false; then
    echo ---
    echo "test-one-asdl-gc $rel_path"
    echo ---
  fi

  local test_src=_gen/${rel_path}_asdl_test.cc
  local bin=_bin/cxx-asan/${rel_path}_asdl_test
  mkdir -p $(dirname $test_src) $(dirname $bin)

  cat >$test_src <<EOF
#include "_gen/${rel_path}.asdl.h"

int main() {
  printf("OK ${test_src}\\n");
  return 0;
}
EOF

  compile_and_link cxx asan '' $bin \
    _gen/${rel_path}.asdl.cc \
    prebuilt/asdl/runtime.mycpp.cc \
    "${GC_RUNTIME[@]}" \
    $test_src \
    "$@"

  run-test $bin $compiler $variant
}

all-asdl-gc() {
  ### All ASDL compilation tests

  local compiler=${1:-cxx}
  local variant=${2:-asan}

  # Invoke ASDL compiler on everything
  build/cpp.sh gen-asdl
  ninja _gen/frontend/id_kind.asdl.cc

  # Now make sure they can compile

  # syntax.asdl is a 'use' dependency; 'id' is implicit there is no GC variant
  # for id_kind_asdl
  one-asdl-gc $compiler $variant \
    core/runtime _gen/frontend/syntax.asdl.cc _gen/frontend/id_kind.asdl.cc

  one-asdl-gc $compiler $variant \
    frontend/syntax _gen/frontend/id_kind.asdl.cc
}

unit() {
  ### Run unit tests

  local compiler=${1:-cxx}
  local variant=${2:-asan}

  gen-cpp-test $compiler $variant
  echo

  # integration between ASDL and the GC heap
  gc-test $compiler $variant
  echo

  # test each ASDL file on its own, perhaps with the garbage-collected ASDL runtime
  all-asdl-gc $compiler $variant
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
