#!/usr/bin/env bash

set -o nounset
set -o pipefail
set -o errexit

# This variable shouldn't conflict with other modules.
#
# TODO: It would be much nicer to export a FUNCTION "cxx" rather than a
# variable $CXX.
_THIS_DIR=$(dirname ${BASH_SOURCE[0]})
readonly _THIS_DIR

# TODO: This changes depending on the version.  Maybe there should be a 'clang'
# function for things that really require clang, like code coverage and so
# forth.
readonly CLANG_DIR_RELATIVE='_deps/clang+llvm-5.0.1-x86_64-linux-gnu-ubuntu-16.04'
readonly CLANG_DIR=$_THIS_DIR/../$CLANG_DIR_RELATIVE
readonly CLANG=$CLANG_DIR/bin/clang
readonly CLANGXX=$CLANG_DIR/bin/clang++

# User can set CXX=, like they can set CC= for oil.ovm
if test -z "${CXX:-}"; then
  if test -f $CLANGXX; then
    # note: Clang doesn't inline MatchOshToken!
    CXX=$CLANGXX
  else
    # equivalent of 'cc' for C++ langauge
    # https://stackoverflow.com/questions/172587/what-is-the-difference-between-g-and-gcc
    CXX='c++'
  fi
fi

# Compiler flags we want everywhere.
# note: -Weverything is more than -Wall, but too many errors now.
CXXFLAGS='-std=c++11 -Wall'

readonly CLANG_COV_FLAGS='-fprofile-instr-generate -fcoverage-mapping'
readonly CLANG_LINK_FLAGS=''

readonly PY27=Python-2.7.13

readonly PREPARE_DIR=_devbuild/cpython-full

# Used by misc/bin.sh and opy/build.sh
readonly OIL_SYMLINKS=(oil oilc osh oshc tea sh true false readlink)
readonly OPY_SYMLINKS=(opy opyc)


log() {
  echo "$@" >&2
}

die() {
  log "FATAL: $@"
  exit 1
}

source-detected-config-or-die() {
  if ! source _build/detected-config.sh; then
    # Make this error stand out.
    echo
    echo "FATAL: can't find _build/detected-config.h.  Run './configure'"
    echo
    exit 1
  fi
}
