#!/usr/bin/env bash
#
# Usage:
#   ./demo.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd $(dirname $0)/..; pwd)
readonly REPO_ROOT

source $REPO_ROOT/build/common.sh  # $BASE_CXXFLAGS, $CLANG_DIR_RELATIVE, $PREPARE_DIR

# -Wpedantic flags the flexible array char opaque[] pattern;
CPPFLAGS="$BASE_CXXFLAGS -O0 -g -fsanitize=address -Wpedantic"
# export ASAN_OPTIONS='detect_leaks=0'

deps() {
  # needed to compile with -m32
  sudo apt install gcc-multilib g++-multilib
}

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
  cpp-compile-run demo/gc_containers.cc "$@"
}

allocator() {
  local bin=_bin/gc_heap
  cpp-compile demo/gc_containers.cc $bin
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
  # -m32 complains about "shadow memory"
  cpp-compile demo/target_lang.cc $bin ../cpp/dumb_alloc.cc gc_containers.cc -I ../cpp
  $bin "$@"
}

# Compile as 32-bit.  Not compatible with ASAN.
target-lang-m32() {
  local bin=_bin/target_lang_32

  # constexpr restrictions lifted
  $CXX -o $bin $BASE_CXXFLAGS -m32 \
    demo/target_lang.cc ../cpp/dumb_alloc.cc -I ../cpp
  $bin "$@"
}

m32-demo() {
  # mask is 1010
  target-lang -t field_mask_demo

  # mask is 10100 !
  target-lang-m32 -t field_mask_demo
}

open() {
  local bin=_bin/open

  cpp-compile demo/open.cc $bin ../cpp/dumb_alloc.cc -I ../cpp

  ls -l $bin
  $bin util.py
}

"$@"
