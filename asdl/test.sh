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

# Could we turn on the leak detector for the GC tests?
export ASAN_OPTIONS='detect_leaks=0'

asdl-tool() {
  PYTHONPATH='.:vendor/' asdl/tool.py "$@"
}

readonly TMP_DIR='_build/asdl-test'

gen-cpp-test() {
  local compiler=${1:-cxx}
  local variant=${1:-asan}

  local tmp_dir=$TMP_DIR
  local bin_dir="_bin/$compiler-$variant/asdl"

  mkdir -p $tmp_dir $bin_dir

  local prefix=$tmp_dir/typed_arith_asdl
  asdl-tool cpp asdl/typed_arith.asdl $prefix

  local prefix2=$tmp_dir/demo_lib_asdl
  asdl-tool cpp asdl/demo_lib.asdl $prefix2

  local prefix3=$tmp_dir/typed_demo_asdl
  asdl-tool cpp asdl/typed_demo.asdl $prefix3

  wc -l $prefix* $prefix2*

  local bin=$bin_dir/gen_cpp_test

  compile_and_link $compiler $variant '-D LEAKY_BINDINGS' $bin \
    asdl/gen_cpp_test.cc \
    asdl/runtime.cc \
    mycpp/mylib_old.cc \
    mycpp/gc_heap.cc \
    mycpp/leaky_types.cc \
    _build/cpp/hnode_asdl.cc \
    $tmp_dir/typed_arith_asdl.cc \
    $tmp_dir/typed_demo_asdl.cc 

  local log_dir="test/$compiler-$variant/asdl"
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

  # for hnode_asdl.gc.cc
  build/dev.sh oil-asdl-to-cpp

  local tmp_dir=$TMP_DIR
  local bin_dir=_bin/$compiler-$variant/asdl
  mkdir -p $tmp_dir $bin_dir

  local prefix2=$tmp_dir/demo_lib_asdl
  asdl-tool cpp asdl/demo_lib.asdl $prefix2

  local prefix3=$tmp_dir/typed_demo_asdl
  asdl-tool cpp asdl/typed_demo.asdl $prefix3

  local bin=$bin_dir/gc_test

  # uses typed_arith_asdl.h, runtime.h, hnode_asdl.h, asdl_runtime.h
  compile_and_link $compiler $variant '' $bin \
    asdl/gc_test.cc \
    mycpp/gc_heap.cc \
    mycpp/gc_builtins.cc \
    mycpp/gc_mylib.cc \
    mycpp/leaky_types.cc \
    asdl/runtime.cc \
    _build/cpp/hnode_asdl.cc \
    $tmp_dir/demo_lib_asdl.cc \
    $tmp_dir/typed_demo_asdl.cc

  local log_dir="test/$compiler-$variant/asdl"
  mkdir -p $log_dir
  local log="$log_dir/gc_test.log"
  log "RUN $bin > $log"
  $bin "$@" > "$log"
}

hnode-asdl-gc() {
  ### Test that hnode can compile by itself

  local tmp_dir=$TMP_DIR
  local bin_dir=_bin/cxx-asan/asdl
  mkdir -p $tmp_dir $bin_dir

  cat >$tmp_dir/hnode_asdl_test.cc <<'EOF'
#include "_build/cpp/hnode_asdl.h"

int main() {
  printf("OK hnode_asdl_test\n");
  return 0;
}
EOF

  local bin=$bin_dir/hnode_asdl_test

  compile_and_link cxx asan '' $bin \
    _build/cpp/hnode_asdl.cc \
    $tmp_dir/hnode_asdl_test.cc

  log "RUN $bin"
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
  local bin_dir=_bin/cxx-asan/asdl
  mkdir -p $tmp_dir $bin_dir

  cat >$tmp_dir/${name}_asdl_test.cc <<EOF
#include "_build/cpp/${name}_asdl.h"

int main() {
  printf("OK ${name}_asdl_test\\n");
  return 0;
}
EOF

  local bin=$bin_dir/${name}_asdl_test

  compile_and_link cxx asan '' $bin \
    _build/cpp/${name}_asdl.cc \
    asdl/runtime.cc \
    mycpp/gc_heap.cc \
    mycpp/gc_builtins.cc \
    mycpp/gc_mylib.cc \
    $tmp_dir/${name}_asdl_test.cc \
    "$@"

  log "RUN $bin"
  $bin
}

all-asdl-gc() {
  ### All ASDL compilation tests

  # Invoke ASDL compiler on everything
  build/dev.sh oil-asdl-to-cpp

  # Now make sure they can compile
  hnode-asdl-gc
  one-asdl-gc types

  # syntax.asdl is a 'use' dependency; 'id' is implicit
  # there is no GC variant for id_kind_asdl
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

"$@"
