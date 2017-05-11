#!/bin/bash
#
# Usage:
#   ./prepare.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/common.sh

# we're always doing it without threads for now.  not sure about signal module
# just yet.  have to implement "trap"?
configure() {
  cd $PY27
  time ./configure --without-threads
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
  cd $PY27
  make clean
  # Speed it up with -O0.
  # NOTE: CFLAGS clobbers some Python flags, so use EXTRA_CFLAGS.

  time make -j $JOBS EXTRA_CFLAGS='-O0'
  #time make -j 7 CFLAGS='-O0'
}

"$@"
