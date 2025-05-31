#!/usr/bin/env bash
#
# Test OSH against any shell
#
# Usage:
#   test/spec-any.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/task-five.sh

source test/common.sh
source test/spec-common.sh

OSH=_bin/cxx-asan/osh
ninja $OSH
OSH=$PWD/$OSH

# To compare against:
# - toysh
# - brush
# - rusty_bash
# - ksh93 - Debian package

download-toybox() {
  #mkdir -p ~/src
  wget --directory ~/src --no-clobber \
    https://landley.net/toybox/downloads/toybox-0.8.12.tar.gz
}

readonly TOYBOX_DIR=~/src/toybox-0.8.12

build-toybox() {
  # warning: using unfinished code
  pushd $TOYBOX_DIR
  make sh
  popd
}

readonly BRUSH_DIR=~/install/brush
download-brush() {
  # The musl libc build works on my old Ubuntu VM, because it's statically linked
  # The GNU one doesn't work
  wget --directory $BRUSH_DIR --no-clobber \
    https://github.com/reubeno/brush/releases/download/brush-shell-v0.2.18/brush-x86_64-unknown-linux-musl.tar.gz
    #https://github.com/reubeno/brush/releases/download/brush-shell-v0.2.18/brush-x86_64-unknown-linux-gnu.tar.gz
}

BRUSH=$BRUSH_DIR/brush

# these are all roughly ksh compatible
readonly -a SHELLS=(bash mksh ksh $TOYBOX_DIR/sh $OSH)

run-file() {
  local spec_name=$1
  shift  # Pass list of shells
  
  sh-spec spec/$spec_name.test.sh "$@"
}

compare() {
  local spec_name=${1:-smoke}
  run-file $spec_name "${SHELLS[@]}"
}

task-five "$@"
