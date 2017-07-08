#!/usr/bin/env bash
#
# Do a full CPython build out of tree, so we can walk dependencies dynamically.
#
# The 'app-deps' and 'runpy-deps' build steps require this.
#
# Usage:
#   ./prepare.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh

configure() {
  local dir=$PREPARE_DIR

  rm -r -f $dir
  mkdir -p $dir

  local conf=$PWD/$PY27/configure 

  cd $dir 
  time $conf --without-threads
}

# Clang makes this faster.  We have to build all modules so that we can
# dynamically discover them with py-deps.
#
# Takes about 27 seconds on a fast i7 machine.
# Ubuntu under VirtualBox on MacBook Air with 4 cores (3 jobs): 1m 25s with
# -O2, 30 s with -O0.  The Make part of the build is parallelized, but the
# setup.py part is not!

readonly JOBS=$(( $(nproc) - 1 ))

build-python() {
  cd $PREPARE_DIR
  make clean
  # Speed it up with -O0.
  # NOTE: CFLAGS clobbers some Python flags, so use EXTRA_CFLAGS.

  time make -j $JOBS EXTRA_CFLAGS='-O0'
  #time make -j 7 CFLAGS='-O0'
}

"$@"
