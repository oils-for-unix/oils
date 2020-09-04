#!/bin/bash
#
# Usage:
#   ./demo.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly THIS_DIR=$(cd $(dirname $0) && pwd)
readonly REPO_ROOT=$(cd $THIS_DIR/.. && pwd)

source $REPO_ROOT/build/common.sh  # for $CLANG_DIR_RELATIVE, $PREPARE_DIR

CPPFLAGS="$CXXFLAGS -O0 -g -fsanitize=address"
export ASAN_OPTIONS='detect_leaks=0'  # like build/mycpp.sh

# Copied from mycpp/run.sh
cpp-compile() {
  local main_cc=$1
  local bin=$2
  shift 2

  mkdir -p _bin
  $CXX -o $bin $CPPFLAGS -I . $main_cc "$@" -lstdc++
}

cpp-compile-run() {
  local main_cc=$1
  shift

  local name=$(basename $main_cc .cc)
  local bin=_bin/$name

  cpp-compile $main_cc $bin "$@"
  $bin
}

square-heap() {
  cpp-compile-run demo/square_heap.cc "$@"
}

gc-heap() {
  cpp-compile-run demo/gc_heap.cc "$@"
}

simple-gc() {
  cpp-compile-run demo/simple_gc.cc "$@"
}

allocator() {
  local bin=_bin/gc_heap
  cpp-compile demo/gc_heap.cc $bin
  $bin allocator
}

max-rss() {
  /usr/bin/time --format '%M' -- "$@"
}

# TODO: A better test it to compare dumb_alloc vs. .tcmalloc vs. normal malloc
overhead() {  
  # allocate 1,000,000 bytes in different batches
  max-rss _bin/gc_heap 10
  max-rss _bin/gc_heap 100
  max-rss _bin/gc_heap 1000
  max-rss _bin/gc_heap 10000
  max-rss _bin/gc_heap 100000
  max-rss _bin/gc_heap 1000000
}

target-lang() {
  local bin=_bin/target_lang 
  cpp-compile demo/target_lang.cc $bin ../cpp/dumb_alloc.cc -I ../cpp
  $bin "$@"
}

open() {
  local bin=_bin/open

  cpp-compile demo/open.cc $bin ../cpp/dumb_alloc.cc -I ../cpp

  ls -l $bin
  $bin util.py
}

"$@"
