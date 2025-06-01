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

# Metrics
# - binary size - stripped
# - lines of source code - I think we get this from DWARF debug info
#   - which means we need an unstripped binary
# - unsafe functions / methods?
#   - cargo geiger has this a bit

readonly BRUSH_DIR=~/install/brush

# Note: we have the repo too
download-brush-binary() {
  # The musl libc build works on my old Ubuntu VM, because it's statically linked
  # The GNU one doesn't work
  wget --directory $BRUSH_DIR --no-clobber \
    https://github.com/reubeno/brush/releases/download/brush-shell-v0.2.18/brush-x86_64-unknown-linux-musl.tar.gz
    #https://github.com/reubeno/brush/releases/download/brush-shell-v0.2.18/brush-x86_64-unknown-linux-gnu.tar.gz
}

#BRUSH=$BRUSH_DIR/brush

# these are all roughly ksh compatible
readonly -a SHELLS=(bash mksh ksh $TOYBOX_DIR/sh $OSH)


download-toybox() {
  #mkdir -p ~/src
  wget --directory ~/src --no-clobber \
    https://landley.net/toybox/downloads/toybox-0.8.12.tar.gz
}

readonly TOYBOX_DIR=~/src/toybox-0.8.12

build-toybox() {
  pushd $TOYBOX_DIR

  make toybox
  # warning: using unfinished code
  make sh

  popd
}

update-rust() {
  . ~/.cargo/env
  time rustup update
}

build-brush() {
  pushd ../../shells/brush

  . ~/.cargo/env

  # Test incremental build speed
  # - debug: 3.8 seconds
  # - release: 1:06 minutes !
  # touch brush-core/src/shell.rs

  # 41s
  time cargo build
  echo

  # 1m 49s
  # It builds a stripped binary by default - disable that for metrics
  RUSTFLAGS='-C strip=none' time cargo build --release
  echo

  popd
}

build-sush() {
  pushd ../../shells/rusty_bash

  . ~/.cargo/env

  # Test incremental build speed
  # - debug: 1 second
  # - release: 6 seconds
  #touch src/core.rs

  # 10 seconds
  time cargo build
  echo

  # 15 seconds
  time cargo build --release
  echo

  popd
}

binary-sizes() {
  pushd ../../shells/brush
  strip -o target/release/brush.stripped target/release/brush
  # stripped: 6.8 MB
  ls -l -h target/release
  popd

  pushd ../../shells/rusty_bash
  strip -o target/release/sush.stripped target/release/sush
  # stripped: 3.7 MB
  ls -l -h target/release
  echo
  popd
}

symbols() {
  pushd ../../shells/brush
  #file target/release/brush

  echo 'BRUSH'
  # 6140
  nm target/release/brush | wc -l
  popd

  pushd ../../shells/rusty_bash
  # Not stripped
  #file target/release/sush

  echo 'SUSH'
  # 10380
  nm target/release/sush | wc -l
  # More symbols
  # nm target/debug/sush | wc -l
  popd

  #local osh=_bin/cxx-opt/bin/oils_for_unix.mycpp.stripped
  local osh=_bin/cxx-opt/bin/oils_for_unix.mycpp
  local dbg=_bin/cxx-dbg/bin/oils_for_unix.mycpp
  ninja $osh 

  echo 'OSH'
  # 9810 - lots of string literals?
  nm $osh | wc -l
  #nm $osh | less

  #ninja $dbg
  # 17570
  #nm $dbg | wc -l
}

install-geiger() {
  # https://github.com/geiger-rs/cargo-geiger
  . ~/.cargo/env

  # 2:34 minutes
  cargo install --locked cargo-geiger
}

geiger-report() {
  pushd ../../shells/rusty_bash

  . ~/.cargo/env

  # this cleans the build
  #
  # Functions  Expressions  Impls   Traits  Methods
  # 181/1056   9377/45040   114/158 30/32   463/2887
  #
  # x/y
  # x = unsafe used by build
  # y = unsafe in crate

  # ~7 seconds
  time cargo geiger 

  popd
}

#
# Spec Tests
#

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
