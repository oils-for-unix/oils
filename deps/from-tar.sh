#!/usr/bin/env bash
#
# Handle build dependencies that are in tarballs.
#
# Usage:
#   deps/from-tar.sh <function name>
#
# Examples:
#   deps/from-tar.sh download-re2c
#   deps/from-tar.sh build-re2c
#
# The executable will be in ../oil_DEPS/re2c/re2c.

set -o nounset
set -o pipefail
set -o errexit

REPO_ROOT=$(cd "$(dirname $0)/.."; pwd)
readonly REPO_ROOT

readonly DEPS_DIR=$REPO_ROOT/../oil_DEPS

source build/common.sh  # $PREPARE_DIR, $PY27

clean-temp() {
  ### Works for layer-bloaty now.  TODO: re2c, cmark, Python 3, spec-bin
  rm -r -f -v _cache/
}

configure-python() {
  ### for both 2.7 OVM slice and 3.10 mycpp

  local dir=${1:-$PREPARE_DIR}
  local conf=${2:-$PWD/$PY27/configure}

  rm -r -f $dir
  mkdir -p $dir

  pushd $dir 
  time $conf
  popd
}

# Clang makes this faster.  We have to build all modules so that we can
# dynamically discover them with py-deps.
#
# Takes about 27 seconds on a fast i7 machine.
# Ubuntu under VirtualBox on MacBook Air with 4 cores (3 jobs): 1m 25s with
# -O2, 30 s with -O0.  The Make part of the build is parallelized, but the
# setup.py part is not!

readonly NPROC=$(nproc)
readonly JOBS=$(( NPROC == 1 ? NPROC : NPROC-1 ))

build-python() {
  local dir=${1:-$PREPARE_DIR}

  pushd $dir
  make clean
  time make -j $JOBS
  popd
}

layer-cpython() {
  ### For bootstrapping OVM build

  # TODO: can we do this with a wedge?
  # $PREPARE_DIR is ../oil_DEPS/cpython-full, which we want to get rid of
  configure-python
  build-python
}

download-wild() {
  ### Done outside the container

  mkdir -p $REPO_ROOT/_cache
  wget --directory $REPO_ROOT/_cache --no-clobber \
    https://www.oilshell.org/blob/wild/wild-source.tar.gz
}

extract-wild() {
  ### Done in the container build

  mkdir -p $DEPS_DIR/wild/src
  pushd $DEPS_DIR/wild/src
  tar --extract -z < $REPO_ROOT/_cache/wild-source.tar.gz
  popd
}

download-souffle() {
  mkdir -p $REPO_ROOT/_cache
  wget --no-clobber --directory $REPO_ROOT/_cache \
    https://github.com/souffle-lang/souffle/archive/refs/tags/2.4.1.tar.gz
}

extract-souffle() {
  mkdir -p $DEPS_DIR/souffle/src
  pushd $DEPS_DIR/souffle/src
  tar --extract -z -f $REPO_ROOT/_cache/2.4.1.tar.gz
  popd
}

build-souffle() {
  pushd $DEPS_DIR/souffle/src/souffle-2.4.1
  rm -rf build
  cmake -DSOUFFLE_USE_CURSES=OFF \
    -DSOUFFLE_USE_SQLITE=OFF \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=$DEPS_DIR/souffle \
    -DSOUFFLE_ENABLE_TESTING=OFF \
    -DSOUFFLE_TEST_EXAMPLES=OFF \
    -DSOUFFLE_TEST_EVALUATION=OFF \
    -S . -B build
  cmake --build build -j 8 --target install
}

layer-souffle() {
  download-souffle
  extract-souffle
  build-souffle
}

"$@"
