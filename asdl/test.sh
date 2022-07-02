#!/usr/bin/env bash
#
# Tests for ASDL.
#
# Usage:
#   asdl/test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)

source build/common.sh  # BASE_CXXFLAGS, etc.
source cpp/NINJA-steps.sh  # compile_and_link

CPPFLAGS="$BASE_CXXFLAGS -g -fsanitize=address"  # for debugging tests

asdl-tool() {
  PYTHONPATH='.:vendor/' asdl/tool.py "$@"
}

readonly TMP_DIR='_build/asdl-test'

gen-cpp-test() {
  export ASAN_OPTIONS='detect_leaks=0'

  local tmp_dir=$TMP_DIR
  local out_dir=_bin/cxx-asan/asdl

  mkdir -p $tmp_dir $out_dir

  local prefix=$tmp_dir/typed_arith_asdl
  asdl-tool cpp asdl/typed_arith.asdl $prefix

  local prefix2=$tmp_dir/demo_lib_asdl
  asdl-tool cpp asdl/demo_lib.asdl $prefix2

  local prefix3=$tmp_dir/typed_demo_asdl
  asdl-tool cpp asdl/typed_demo.asdl $prefix3

  wc -l $prefix* $prefix2*

  local bin=$out_dir/gen_cpp_test

  compile_and_link cxx asan '-D LEAKY_BINDINGS' $bin \
    asdl/gen_cpp_test.cc \
    asdl/runtime.cc \
    mycpp/mylib_leaky.cc \
    mycpp/gc_heap.cc \
    _build/cpp/hnode_asdl.cc \
    $tmp_dir/typed_arith_asdl.cc \
    $tmp_dir/typed_demo_asdl.cc 

  $bin "$@"
}

gc-test() {
  # TODO: remove this after it works with the garbage collector!
  export ASAN_OPTIONS='detect_leaks=0'

  # for hnode_asdl.gc.cc
  build/dev.sh oil-asdl-to-cpp-gc

  local tmp_dir=$TMP_DIR
  local out_dir=_bin/cxx-asan/asdl
  mkdir -p $tmp_dir $out_dir

  local prefix2=$tmp_dir/demo_lib_asdl.gc
  GC=1 asdl-tool cpp asdl/demo_lib.asdl $prefix2

  local prefix3=$tmp_dir/typed_demo_asdl.gc
  GC=1 asdl-tool cpp asdl/typed_demo.asdl $prefix3

  local bin=$out_dir/asdl_gc_test

  # uses typed_arith_asdl.h, runtime.h, hnode_asdl.h, asdl_runtime.h
  compile_and_link cxx asan '' $bin \
    asdl/gc_test.cc \
    mycpp/gc_heap.cc \
    mycpp/my_runtime.cc \
    mycpp/mylib2.cc \
    asdl/runtime.gc.cc \
    _build/cpp/hnode_asdl.gc.cc \
    $tmp_dir/demo_lib_asdl.gc.cc \
    $tmp_dir/typed_demo_asdl.gc.cc

  $bin "$@"
}

hnode-asdl-gc() {
  ### Test that hnode can compile by itself

  local tmp_dir=$TMP_DIR
  local out_dir=_bin/cxx-asan/asdl
  mkdir -p $tmp_dir $out_dir

  cat >$tmp_dir/hnode_asdl_test.cc <<'EOF'
#include "_build/cpp/hnode_asdl.gc.h"

int main() {
  printf("OK hnode_asdl_test\n");
  return 0;
}
EOF

  local bin=$out_dir/hnode_asdl_test

  compile_and_link cxx asan '' $bin \
    _build/cpp/hnode_asdl.gc.cc \
    $tmp_dir/hnode_asdl_test.cc

  $bin
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

  local tmp_dir=$TMP_DIR
  local out_dir=_bin/cxx-asan/asdl
  mkdir -p $tmp_dir $out_dir

  cat >$tmp_dir/${name}_asdl_test.cc <<EOF
#include "_build/cpp/${name}_asdl.gc.h"

int main() {
  printf("OK ${name}_asdl_test\\n");
  return 0;
}
EOF

  local bin=$out_dir/${name}_asdl_test

  compile_and_link cxx asan '' $bin \
    _build/cpp/${name}_asdl.gc.cc \
    asdl/runtime.gc.cc \
    mycpp/gc_heap.cc \
    mycpp/my_runtime.cc \
    mycpp/mylib2.cc \
    $tmp_dir/${name}_asdl_test.cc \
    "$@"

  $bin
}

all-asdl-gc() {
  ### All ASDL compilation tests

  # Invoke ASDL compiler on everything
  build/dev.sh oil-asdl-to-cpp-gc

  # Now make sure they can compile
  hnode-asdl-gc
  one-asdl-gc types

  # syntax.asdl is a 'use' dependency; 'id' is implicit
  # there is no GC variant for id_kind_asdl
  one-asdl-gc runtime _build/cpp/syntax_asdl.gc.cc _build/cpp/id_kind_asdl.cc

  one-asdl-gc syntax _build/cpp/id_kind_asdl.cc
}

unit() {
  asdl/test.sh gen-cpp-test
  asdl/test.sh gc-test  # integration between ASDL and the GC heap

  # test each ASDL file on its own, perhaps with the garbage-collected ASDL runtime
  asdl/test.sh all-asdl-gc
}

"$@"
